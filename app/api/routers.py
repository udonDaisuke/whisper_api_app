from fastapi import APIRouter, UploadFile, File, HTTPException

from pathlib import Path
import tempfile
from contextlib import suppress

from app.core.config import settings
from app.services.whisper import transcribe_with_path

router = APIRouter()

@router.get("/health")
def health_chk():
    return {"status": "OK"}

@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    # 拡張子の取得
    suffix = Path(file.filename or "").suffix or ".tmp"

    # 一時ファイルの作成
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)

    try:
        # 一時ファイルをバイナリ書き込みモードで開く
        with tmp_path.open("wb") as out:
            while True:
                # アップロードファイルを指定サイズずつ非同期で読む
                chunk = await file.read(settings.UPLOAD_CHUNK_BYTES)
                if not chunk:
                    # データがなくなったらループ終了
                    break
                # 読み込んだデータを一時ファイルに書き込む
                out.write(chunk)
        # 一時ファイルのパスを渡して文字起こし処理を実行
        return transcribe_with_path(tmp_path)
    except Exception as e:
        # 何らかの例外が発生した場合はHTTP 500エラーで返す
        raise HTTPException(status_code=500, detail=str(e)) 
    finally:
        # 最後に必ず一時ファイルを削除（ファイルがなくてもエラーにしない）
        with suppress(FileNotFoundError):
            tmp_path.unlink()
