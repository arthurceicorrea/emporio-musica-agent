"""Semantic and lexical hybrid policy retriever backed by ChromaDB."""

from __future__ import annotations

import re
from typing import Any

from src.rag.ingest_pdf import (
     _strip_accents,
    get_chroma_collection,
    index_policies_to_chroma,
)

# Domain topic keywords mapped to policy section prefixes for high-precision boosting
TOPIC_SECTION_HINTS: dict[str, tuple[str, ...]] = {
    "1": ("sobre", "missao", "cnpj", "endereco", "rua 14 de maio", "telefone", "email", "acessorios", "cordas", "palhetas", "cabos", "amplificadores", "pedais"),
    "2": ("horario", "funcionamento", "expediente", "abre", "fecha", "sabado", "domingo", "feriado"),
    "3": ("pagamento", "pix", "cartao", "credito", "debito", "boleto", "parcelamento", "parcela", "sem juros", "combinacao"),
    "4": ("troca", "devolucao", "arrependimento", "reembolso", "defeito", "preferencia", "boquilha", "setup"),
    "5": ("frete", "entrega", "motoboy", "campo grande", "correios", "pac", "sedex", "jadlog", "rastreamento", "rastreio", "seguro", "avaria"),
    "6": ("promocao", "promocoes", "desconto", "cumulativo", "black friday", "aniversario", "rain check"),
    "7": ("whatsapp", "atendimento", "tom de voz", "fora de estoque", "esgotado", "descontinuado", "reclamacao"),
    "8": ("garantia", "legal", "fabricante", "90 dias", "mau uso", "desgaste"),
    "9": ("privacidade", "lgpd", "dados pessoais", "exclusao"),
    "10": ("disposicoes finais", "gerencia", "versao"),
}


class PolicyRetriever:
    """Retriever that queries ChromaDB and applies domain-aware section boosting."""

    def __init__(self, auto_index: bool = True) -> None:
        if auto_index:
            index_policies_to_chroma(force_reindex=False)
        self.collection = get_chroma_collection()

    def search(self, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        """Retrieve the most relevant store policy sections for a natural language query."""
        total_docs = self.collection.count()
        if total_docs == 0:
            index_policies_to_chroma(force_reindex=True)
            total_docs = self.collection.count()

        n_results = min(max(top_k * 2, 8), total_docs)
        raw_results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        docs = (raw_results.get("documents") or [[]])[0]
        metas = (raw_results.get("metadatas") or [[]])[0]
        distances = (raw_results.get("distances") or [[]])[0]

        normalized_query = _strip_accents(query)
        query_tokens = set(re.findall(r"[a-z0-9]+", normalized_query))

        # Determine boosted parent section prefixes based on domain hints
        boosted_prefixes: set[str] = set()
        for sec_prefix, keywords in TOPIC_SECTION_HINTS.items():
            if any(kw in normalized_query for kw in keywords):
                boosted_prefixes.add(sec_prefix)

        scored_items: list[dict[str, Any]] = []
        for doc_text, meta, dist in zip(docs, metas, distances):
            vector_score = 1.0 - float(dist)
            sec_id = str(meta.get("section_id", ""))
            sec_prefix = sec_id.split(".")[0]

            # Lexical overlap bonus
            normalized_doc = _strip_accents(doc_text)
            lexical_hits = sum(1 for tok in query_tokens if len(tok) > 2 and tok in normalized_doc)
            lexical_bonus = min(lexical_hits * 0.08, 0.40)

            # Section hint bonus
            section_bonus = 0.25 if sec_prefix in boosted_prefixes else 0.0

            final_score = round(vector_score + lexical_bonus + section_bonus, 4)
            scored_items.append(
                {
                    "section_id": sec_id,
                    "section_title": meta.get("section_title", ""),
                    "parent_section": meta.get("parent_section", ""),
                    "page_number": meta.get("page_number", 1),
                    "score": final_score,
                    "content": doc_text,
                }
            )

        scored_items.sort(key=lambda item: item["score"], reverse=True)
        return scored_items[:top_k]


def retrieve_policy_context(query: str, top_k: int = 4) -> str:
    """Format retrieved store policy sections into a clean context string for the LLM."""
    retriever = PolicyRetriever(auto_index=True)
    results = retriever.search(query=query, top_k=top_k)
    if not results:
        return "Nenhuma diretriz encontrada no Manual de Políticas da Empório da Música."

    formatted_blocks: list[str] = []
    for item in results:
        header = (
            f"--- Seção {item['section_id']} ({item['section_title']}) | "
            f"Página {item['page_number']} ---"
        )
        formatted_blocks.append(f"{header}
{item['content']}")
    return "

".join(formatted_blocks)
