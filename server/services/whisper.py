import os, tempfile, shutil
from pathlib import Path
import whisper
from server.core.config import settings


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

def transcribe_with_path(path: Path) -> dict:
    model = _get_model()
    print(path.exists())
    try:
        result = model.transcribe(
            str(path),
            language="ja",   # 例
            fp16=False,      # CPUなら False 推奨
            task="transcribe",
            # 分割ストリーミング用
            condition_on_previous_text=False,
            temperature=0.0,
            beam_size=5,
            no_speech_threshold=0.4,
        )
    except Exception as e:
        print(f"Error during transcription: {e}")
        raise
    # openai-whisperは dict を返す
    print(f"transcribe result: {result}")
    text = (result.get("text") or "").strip()
    segs = result.get("segments") or []
    duration = segs[-1]["end"] if segs else None
    lang = result.get("language")
    return {"language": lang, "duration": duration, "text": text}