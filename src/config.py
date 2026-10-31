"""Centralized, environment-backed configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent

# Load the project's .env file
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_base_url: str
    openai_model: str
    openai_embedding_model: str
    database_path: Path
    chroma_path: Path
    chroma_collection: str
    human_review_threshold: float
    esg_api_key: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        threshold = float(
            os.getenv("HUMAN_REVIEW_THRESHOLD", "0.82")
        )

        if not 0 <= threshold <= 1:
            raise ValueError(
                "HUMAN_REVIEW_THRESHOLD must be between 0 and 1"
            )

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_base_url=os.getenv(
                "OPENAI_BASE_URL",
                "https://api.openai.com/v1",
            ),
            openai_model=os.getenv(
                "OPENAI_MODEL",
                "gpt-4o-mini",
            ),
            openai_embedding_model=os.getenv(
                "OPENAI_EMBEDDING_MODEL",
                "text-embedding-3-small",
            ),
            database_path=Path(
                os.getenv(
                    "DATABASE_PATH",
                    str(ROOT_DIR / "portfolio.sqlite3"),
                )
            ),
            chroma_path=Path(
                os.getenv(
                    "CHROMA_PATH",
                    str(ROOT_DIR / ".chroma_db"),
                )
            ),
            chroma_collection=os.getenv(
                "CHROMA_COLLECTION",
                "esg_compliance_standards",
            ),
            human_review_threshold=threshold,
            esg_api_key=os.getenv("ESG_API_KEY") or None,
        )


settings = Settings.from_env()