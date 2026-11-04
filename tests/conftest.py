"""Pytest fixtures for seeding isolated SQLite and ChromaDB test environments."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from src.config import BASE_DIR, DATA_DIR
from src.database.ingest_csv import init_and_seed_database
from src.rag.ingest_pdf import index_policies_to_chroma


def _ensure_challenge_data_present() -> None:
    """Extract challenge CSVs and PDF into DATA_DIR if running in a clean test sandbox."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    expected_csv = DATA_DIR / "desafio_tecnico_ai_eng - products.csv"
    if not expected_csv.exists():
        for zip_candidate in BASE_DIR.glob("*.zip"):
            if "Desafio" in zip_candidate.name or "desafio" in zip_candidate.name.lower():
                with zipfile.ZipFile(zip_candidate, "r") as zf:
                    zf.extractall(BASE_DIR)
                break


@pytest.fixture(scope="session", autouse=True)
def setup_test_databases() -> dict[str, int]:
    """Ensure SQLite relational tables and ChromaDB policy vectors are seeded before tests."""
    _ensure_challenge_data_present()
    counts = init_and_seed_database(force_reseed=True)
    index_policies_to_chroma(force_reindex=True)
    return counts
