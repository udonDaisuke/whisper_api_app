import os, tempfile, shutil
from pathlib import Path
from whisper import load_model
from app.core.config import settings


model = load_model("small")
_model = None

def _get_model() -> load_model:
    global _model
    if _model is None:
        _model = load_model(
            settings.WHISPER_MODEL, 
            device=settings.WHISPER_DEVICE, 
            compute_type=settings.COMPUTE_TYPE
            )
    return _model

def transcribe_with_path(path: Path) -> dict:
    model = _get_model()
    segments, info = model.transcribe(
        str(path),
        language=p.language,
        task=p.task,
        vad_filter=p.vad_filter,
        beam_size=p.beam_size,
        chunk_length=p.chunk_length,
    )
    text = "".join(s.text for s in segments)
    return {"language": info.language, "duration": info.duration, "text": text}