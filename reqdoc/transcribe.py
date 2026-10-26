"""Recording (audio/video) -> list[Segment] using faster-whisper on CPU.

No speaker labels: Whisper only gives text and times. Owners come from names said aloud.
"""
import threading
from collections.abc import Callable
from pathlib import Path

from . import config
from .models import Segment

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".mp4", ".webm", ".ogg", ".aac", ".wma", ".flac", ".mkv", ".mov"}

_model = None
_model_lock = threading.Lock()


def is_recording(path: str | Path) -> bool:
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS


def _get_model():
    global _model
    with _model_lock:
        if _model is None:
            from faster_whisper import WhisperModel

            _model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
        return _model


def model_available() -> bool:
    """True if the Whisper model is already downloaded (no network needed to start a job)."""
    try:
        from faster_whisper.utils import download_model

        download_model(config.WHISPER_MODEL, local_files_only=True)
        return True
    except Exception:
        return False


def _clock(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def transcribe(path: str | Path, progress: Callable[[str, float], None] | None = None) -> list[Segment]:
    model = _get_model()
    segments_iter, info = model.transcribe(
        str(path),
        language=config.WHISPER_LANGUAGE or None,
        vad_filter=True,  # skips silence, which also stops Whisper inventing text there
        beam_size=5,
        condition_on_previous_text=False,  # avoids repetition loops on long recordings
    )
    total = max(info.duration, 1.0)
    out: list[Segment] = []
    for seg in segments_iter:
        text = seg.text.strip()
        if text:
            s = int(seg.start)
            out.append(Segment(timestamp=f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}", text=text))
        if progress:
            progress(f"Transcribing {_clock(seg.end)} of {_clock(total)}", min(seg.end / total, 1.0))
    if not out:
        raise ValueError("No speech was found in the recording. Check the file and its volume.")
    return out


def segments_to_text(segments: list[Segment]) -> str:
    """The [HH:MM:SS] text form saved next to the project; parse_lines reads it back."""
    return "\n".join(f"[{s.timestamp}] {s.text}" if s.timestamp else s.text for s in segments) + "\n"
