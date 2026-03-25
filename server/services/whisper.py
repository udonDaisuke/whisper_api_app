import logging
import os
from pathlib import Path

import whisper

from server.core.config import settings

logger = logging.getLogger(__name__)

# model = load_model("tiny")
_model = None

def _get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        name = str(settings.WHISPER_MODEL).strip().strip('"').strip("'")
        # name が _MODELS にない・おかしい場合は即わかるようチェック
        if name not in whisper._MODELS:
            raise ValueError(f"Unknown model name: {name!r}")
        _model = whisper.load_model(
            name,
            download_root=os.environ.get("XDG_CACHE_HOME") or None,
        )
    return _model

def transcribe_with_path(path: Path, *, language: str | None = None) -> dict:
    model = _get_model()
    logger.debug("transcribe target path exists: %s", path.exists())
    try:
        result = model.transcribe(
            str(path),
            language=language,  # None の場合は Whisper が自動検出
            fp16=False,         # CPU なら False 推奨
            task="transcribe",
            # 分割ストリーミング用
            condition_on_previous_text=False,
            temperature=0.0,
            beam_size=5,
            no_speech_threshold=0.4,
        )
    except Exception as e:
        logger.error("transcription failed: %s", e)
        raise
    # openai-whisperは dict を返す
    logger.debug("transcribe result: %s", result)
    text = (result.get("text") or "").strip()
    segs = result.get("segments") or []
    duration = segs[-1]["end"] if segs else None
    lang = result.get("language")
    return {"language": lang, "duration": duration, "text": text}