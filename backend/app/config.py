import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    db_path: Path
    storage_dir: Path
    data_dir: Path
    models_dir: Path
    groq_api_key: str | None
    llm_api_url: str
    llm_model: str
    frontend_origin: str


def load_settings() -> Settings:
    return Settings(
        db_path=Path(os.environ.get("DATABASE_PATH", REPO_ROOT / "data" / "shoplens.db")),
        storage_dir=Path(os.environ.get("STORAGE_DIR", REPO_ROOT / "storage")),
        data_dir=Path(os.environ.get("DATA_DIR", REPO_ROOT / "data")),
        models_dir=Path(os.environ.get("MODELS_DIR", REPO_ROOT / "backend" / "models")),
        groq_api_key=os.environ.get("GROQ_API_KEY") or None,
        llm_api_url=os.environ.get("LLM_API_URL", "https://api.groq.com/openai/v1/chat/completions"),
        llm_model=os.environ.get("LLM_MODEL", "openai/gpt-oss-120b"),
        frontend_origin=os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173"),
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
