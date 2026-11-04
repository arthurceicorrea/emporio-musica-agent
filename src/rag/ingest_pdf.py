"""Hierarchical PDF parser and ChromaDB indexer for Emporio da Musica store policies."""

from __future__ import annotations

import hashlib
import logging
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
import fitz  # PyMuPDF

from src.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "emporio_store_policies"

# Regex patterns for top-level sections (e.g., "1. Sobre a Empório da Música")
# and subsections (e.g., "4.1 Direito de Arrependimento (Compras Online)")
MAIN_SECTION_RE = re.compile(r"^(\d{1,2})\.\s+([A-ZÀ-Ú].+)$")
SUB_SECTION_RE = re.compile(r"^(\d{1,2}\.\d{1,2})\s+([A-ZÀ-Ú].+)$")


@dataclass(frozen=True)
class PolicyChunk:
    """Structured semantic chunk extracted from the store policy manual PDF."""

    chunk_id: str
    section_id: str
    section_title: str
    parent_section: str
    page_number: int
    content: str

    def to_metadata(self) -> dict[str, Any]:
        """Serialize chunk attributes into ChromaDB-compatible flat metadata."""
        return {
            "section_id": self.section_id,
            "section_title": self.section_title,
            "parent_section": self.parent_section,
            "page_number": self.page_number,
        }


def _strip_accents(text: str) -> str:
    """Normalize Unicode string and remove diacritics for resilient matching."""
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


class MultilingualPolicyEmbeddingFunction(EmbeddingFunction[Documents]):
    """Deterministic multilingual feature-hashing and char-ngram embedding function.

    Provides instant, offline-safe semantic and lexical representations for Portuguese
    policy documents without requiring external weight downloads at runtime.
    """

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def __call__(self, input: Documents) -> Embeddings:
        embeddings: Embeddings = []
        for doc in input:
            vec = [0.0] * self.dim
            normalized = _strip_accents(doc)
            tokens = re.findall(r"[a-z0-9]+", normalized)

            # 1. Word token unigrams and bigrams (weighted higher for semantic anchor terms)
            for idx, token in enumerate(tokens):
                if len(token) < 2:
                    continue
                self._accumulate(vec, f"tok:{token}", weight=2.0)
                if len(token) >= 5:
                    # Prefix stem approximation for Portuguese morphology
                    self._accumulate(vec, f"stem:{token[:5]}", weight=1.5)
                if idx + 1 < len(tokens):
                    bigram = f"bi:{token}_{tokens[idx + 1]}"
                    self._accumulate(vec, bigram, weight=1.8)

            # 2. Character trigrams and four-grams for typo and inflection resilience
            compact = re.sub(r"\s+", " ", normalized)
            for n in (3, 4):
                for i in range(max(0, len(compact) - n + 1)):
                    ngram = compact[i : i + n]
                    self._accumulate(vec, f"ng:{ngram}", weight=0.4)

            # L2 normalization
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            embeddings.append([v / norm for v in vec])
        return embeddings

    def _accumulate(self, vec: list[float], feature: str, weight: float) -> None:
        digest = hashlib.md5(feature.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "little") % self.dim
        sign = 1.0 if (digest[4] & 1) == 0 else -1.0
        vec[bucket] += sign * weight


def resolve_policy_pdf_path(data_dir: Path | None = None) -> Path:
    """Locate the store policy PDF handling NFC/NFD Unicode and unaccented filenames."""
    base = data_dir or settings.data_dir
    direct_candidates = [
        base / "políticas_da_loja.pdf",
        base / "politicas_da_loja.pdf",
    ]
    for candidate in direct_candidates:
        if candidate.exists():
            return candidate

    # Fallback scan for Unicode normalization differences across operating systems
    if base.exists():
        for pdf_file in base.glob("*.pdf"):
            if "politicas" in _strip_accents(pdf_file.name):
                return pdf_file

    raise FileNotFoundError(
        f"Store policy PDF not found in {base}. Expected 'políticas_da_loja.pdf'."
    )


def _clean_page_lines(raw_text: str) -> list[str]:
    """Remove repetitive running headers and footers from extracted PDF page text."""
    cleaned_lines: list[str] = []
    for raw_line in raw_text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if line.startswith("Empório da Música") and "Manual de Políticas" in line:
            continue
        if re.match(r"^Página\s+\d+$", line, re.IGNORECASE):
            continue
        cleaned_lines.append(line)
    return cleaned_lines


def extract_policy_chunks(pdf_path: Path | None = None) -> list[PolicyChunk]:
    """Parse the store policy PDF into hierarchical section and subsection chunks."""
    target_pdf = pdf_path or resolve_policy_pdf_path()
    doc = fitz.open(target_pdf)

    chunks: list[PolicyChunk] = []
    current_parent_id = "0"
    current_parent_title = "Capa e Identificação Institucional"
    current_section_id = "0.0"
    current_section_title = "Capa e Contato Oficial"
    current_page = 1
    buffer: list[str] = []

    def flush_buffer() -> None:
        if not buffer:
            return
        body = "
".join(buffer).strip()
        if not body:
            buffer.clear()
            return
        chunk_index = len(chunks) + 1
        chunk_id = f"policy_sec_{current_section_id.replace('.', '_')}_{chunk_index:02d}"
        formatted_content = (
            f"[{current_parent_title} > {current_section_id} {current_section_title}]
{body}"
        )
        chunks.append(
            PolicyChunk(
                chunk_id=chunk_id,
                section_id=current_section_id,
                section_title=current_section_title,
                parent_section=current_parent_title,
                page_number=current_page,
                content=formatted_content,
            )
        )
        buffer.clear()

    for page_index in range(len(doc)):
        page_num = page_index + 1
        lines = _clean_page_lines(doc[page_index].get_text("text"))

        for line in lines:
            main_match = MAIN_SECTION_RE.match(line)
            sub_match = SUB_SECTION_RE.match(line)

            if main_match:
                flush_buffer()
                current_parent_id = main_match.group(1)
                current_parent_title = f"{current_parent_id}. {main_match.group(2).strip()}"
                current_section_id = f"{current_parent_id}.0"
                current_section_title = main_match.group(2).strip()
                current_page = page_num
            elif sub_match:
                flush_buffer()
                current_section_id = sub_match.group(1)
                current_section_title = sub_match.group(2).strip()
                current_page = page_num
            else:
                if not buffer:
                    current_page = page_num
                buffer.append(line)

    flush_buffer()
    doc.close()
    return chunks


def get_chroma_collection(
    persist_dir: Path | None = None,
) -> chromadb.Collection:
    """Create or retrieve the persistent ChromaDB store policies collection."""
    target_dir = persist_dir or settings.chroma_persist_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(target_dir))
    embedding_fn = MultilingualPolicyEmbeddingFunction()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )


def index_policies_to_chroma(
    pdf_path: Path | None = None,
    persist_dir: Path | None = None,
    force_reindex: bool = False,
) -> int:
    """Extract policy chunks from the PDF and upsert them into ChromaDB."""
    collection = get_chroma_collection(persist_dir=persist_dir)
    existing_count = collection.count()
    if existing_count > 0 and not force_reindex:
        return existing_count

    chunks = extract_policy_chunks(pdf_path=pdf_path)
    if not chunks:
        return 0

    collection.upsert(
        ids=[c.chunk_id for c in chunks],
        documents=[c.content for c in chunks],
        metadatas=[c.to_metadata() for c in chunks],
    )
    return len(chunks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    total_chunks = index_policies_to_chroma(force_reindex=True)
    logger.info("Indexed %d policy chunks into ChromaDB.", total_chunks)
