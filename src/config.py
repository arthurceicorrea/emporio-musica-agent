"""Centralized configuration and path management for Emporio da Musica Agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

# Base project directories
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
STORAGE_DIR: Path = BASE_DIR / "storage"

# Ensure local runtime storage directory exists
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    """Application settings resolved from environment variables."""

    llm_provider: str = os.getenv("LLM_PROVIDER", "google").lower()
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    model_name: str = os.getenv("MODEL_NAME", "gemini-2.5-flash")
    temperature: float = float(os.getenv("TEMPERATURE", "0.2"))

    # Data and persistence paths
    data_dir: Path = DATA_DIR
    policy_pdf_path: Path = DATA_DIR / "políticas_da_loja.pdf"
    database_url: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{STORAGE_DIR / 'emporio.db'}"
    )
    checkpoint_db_path: Path = Path(
        os.getenv("CHECKPOINT_DB_PATH", str(STORAGE_DIR / "checkpoints.db"))
    )
    chroma_persist_dir: Path = Path(
        os.getenv("CHROMA_PERSIST_DIR", str(STORAGE_DIR / "chroma_db"))
    )


settings = Settings()
