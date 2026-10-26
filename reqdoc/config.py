"""Settings loaded once from .env (see .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))
OLLAMA_NUM_GPU = int(os.getenv("OLLAMA_NUM_GPU")) if os.getenv("OLLAMA_NUM_GPU") else None  # 0 = CPU only
OLLAMA_MAX_TOKENS = int(os.getenv("OLLAMA_MAX_TOKENS", "4096"))  # cap per call
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")  # tiny / base / small / medium
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en")  # "" = auto-detect
# Let Microsoft Word fill in each document's table of contents (needs Word on this computer; adds a few seconds)
WORD_TOC = os.getenv("REQDOC_WORD_TOC", "1").strip().lower() not in ("0", "false", "no", "")
FRONTEND_DIST = ROOT / "frontend" / "dist"
CHUNK_TOKENS = int(os.getenv("CHUNK_TOKENS", "6000"))
DATA_DIR = _path(os.getenv("REQDOC_DATA_DIR", "./data"))
GLOSSARY_FILE = _path(os.getenv("GLOSSARY_FILE", "./config/glossary.txt"))
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_glossary() -> str:
    """Glossary text with comments removed ('' if the file is missing or empty)."""
    try:
        lines = GLOSSARY_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    return "\n".join(l.strip() for l in lines if l.strip() and not l.lstrip().startswith("#"))
