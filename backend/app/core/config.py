"""Configuration loader using Pydantic Settings v2 for TruthGuard AI.

Reads from environment variables and .env file.
Guarantees secrets are protected and defaults are provided for local development.
"""

from pathlib import Path
from typing import Optional, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base Paths
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent
    RAW_PDFS_DIR: Path = Path("data/raw_pdfs")
    PROCESSED_DIR: Path = Path("data/processed")
    CHROMA_PERSIST_DIR: Path = Path("data/processed/chroma")
    GOLD_DATA_PATH: Path = Path("data/gold/questions.csv")
    PROMPTS_DIR: Path = Path("prompts")

    # LLM Configuration (Google Gemini)
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API Key")
    GEMINI_MODEL: str = Field(
        default="gemini-1.5-pro",
        description="Google Gemini model identifier for generation and claim extraction",
    )

    # Database Configuration (PostgreSQL)
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://truthguard:truthguard_password@localhost:5432/truthguard",
        description="SQLAlchemy compatible PostgreSQL connection URL",
    )

    # Hugging Face Configuration
    HF_TOKEN: Optional[str] = Field(
        default=None,
        description="Optional Hugging Face token for higher rate limits or model hub",
    )

    # Hardware Device
    DEVICE: Literal["auto", "mps", "cpu", "cuda"] = Field(
        default="auto",
        description="Inference device for PyTorch and Transformers models",
    )

    # Model Names
    EMBEDDING_MODEL_NAME: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="Sentence transformers embedding checkpoint for vector retrieval",
    )
    NLI_MODEL_NAME: str = Field(
        default="MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli",
        description="Hugging Face NLI model checkpoint based on DeBERTa-v3 fine-tuned on MNLI/FEVER/ANLI",
    )

    # Verification & Decision Thresholds
    THETA_E: float = Field(
        default=0.70,
        description="Entailment confidence threshold for Verified label",
        ge=0.0,
        le=1.0,
    )
    THETA_C: float = Field(
        default=0.60,
        description="Contradiction confidence threshold for Contradicted label",
        ge=0.0,
        le=1.0,
    )
    ALPHA: float = Field(
        default=0.50,
        description="Penalty weight s(Unsupported) in risk calculation R",
        ge=0.0,
        le=1.0,
    )
    TAU: float = Field(
        default=0.25,
        description="Risk tolerance threshold for abstention decision (R > tau)",
        ge=0.0,
        le=1.0,
    )
    RELEVANCE_FLOOR: float = Field(
        default=0.30,
        description="Minimum retrieval score below which passages are discarded or marked NO_EVIDENCE",
        ge=0.0,
        le=1.0,
    )
    TOP_K: int = Field(
        default=5,
        description="Number of passages to retrieve for hybrid ranking",
        gt=0,
    )

    # Claim Weighting
    WEIGHT_CRITICAL: float = Field(default=2.0, description="Weight assigned to critical claims")
    WEIGHT_NON_CRITICAL: float = Field(default=1.0, description="Weight assigned to non-critical claims")

    def get_masked_gemini_key(self) -> str:
        """Returns safe representation of Gemini API key without exposing secret."""
        if not self.GEMINI_API_KEY:
            return "<UNSET>"
        if len(self.GEMINI_API_KEY) <= 8:
            return "****"
        return f"{self.GEMINI_API_KEY[:4]}...{self.GEMINI_API_KEY[-4:]}"


# Global cached settings instance
settings = Settings()
