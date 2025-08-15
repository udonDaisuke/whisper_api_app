# app/api/ws.py
from typing import Union
from pathlib import Path
import wave

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi import Cookie,Query,Depends, WebSocketException,status

from app.services.whisper import transcribe_with_path
import tempfile

router = APIRouter()

clients = []

@router.websocket("/ws/test")
async def ws_index(ws:WebSocket):
    await ws.accept()
    while True:
        data = await ws.receive_text()
        await ws.send_text(f"Server response: msg received = [{data}]")

async def get_cookie(
        ws: WebSocket,
        session: Union[str,None] = Cookie(default=None),
        token: Union[str, None] = Query(default=None),
):
    if session is None and token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return session or token


@router.websocket("/ws/test2")
async def ws_index_cookie(ws:WebSocket,cookie:str = Depends(get_cookie)):
    await ws.accept()
    clients.append(ws) # multi-users sharing
    try:
        while True:
            data = await ws.receive_text()
            for client in clients:
                await client.send_text(f"Server response: msg received = [{data}]")
    except WebSocketDisconnect:
        clients.remove(ws)
        await ws.close()

@router.websocket("/ws/transcribe")
async def ws_transcribe(ws: WebSocket):
    # 1) ハンドシェイクを受け入れる（これをしないと403相当で落ちます）
    await ws.accept()

    try:
        # 2) クライアントのstartメッセージ（JSON）を受ける
        start = await ws.receive_json()  # {"type":"start","sample_rate":16000,...} を想定
        # 3) 準備完了を通知
        await ws.send_json({"type": "ready"})

        # 4) 音声フレームを受け取り続ける（最小：捨てる/カウントするだけ）
        total = 0
        while True:
            data = await ws.receive_bytes()   # バイナリ(PCM16)想定
            total += len(data)
            # デモ用に時々partialを返す（本実装ではここで推論に回す）
            if total % (16000 * 2) < len(data):  # 1秒分くらい受けたら
                await ws.send_json({"type":"partial","text": f"[{total} bytes received]"})
    except WebSocketDisconnect:
        # 5) クライアントが切断した
        pass


def write_pcm16_wav(path: str, pcm: bytes, *, sr: int) -> None:
    """PCM16LE mono を WAV (ヘッダ付き) で書き出す"""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)     # 16-bit
        wf.setframerate(sr)    # 例: 16000
        wf.writeframes(pcm)

@router.websocket("/ws/transcribe_audio")
async def ws_transcribe_audio(ws:WebSocket):
    await ws.accept()
    try:
        # 1) start(JSON) を受信（例: {"type":"start","sampleRate":16000,"language":"ja"}）
        start = await ws.receive_json()
        sr = int(start.get("sampleRate") or start.get("sample_rate") or 16000)
        lang = start.get("language") or "ja"
        await ws.send_json({"type": "ready"})

        # 2) 音声受信ループ（最初だけ text/JSON、その後は基本 bytes）
        buf = bytearray()
        window_sec = float(start.get("windowSec") or 1.0)  # 1秒ごとに区切って認識
        chunk_bytes = int(sr * 2 * window_sec)             # 1秒分のバイト数（16bit=2byte）
        
        while True:
            msg = await ws.receive()   # ← text/bytes どちらも来てもOK
            print(f"msg_type: [{msg.get('type')}]\n bytes: None->{msg.get('bytes') is None}")
            t = msg["type"]

            if t == "websocket.receive":
                if (b := msg.get("bytes")) is not None:
                    # バイナリ＝PCM16LE
                    buf.extend(b)               

                    # たまった分を 1秒ごとにWAV化 → Whisper
                    while len(buf) >= chunk_bytes:
                        part = bytes(buf[:chunk_bytes])
                        del buf[:chunk_bytes]

                        with tempfile.NamedTemporaryFile(suffix=".wav",dir="/data/tmp", delete=False) as tmp:
                            write_pcm16_wav(tmp.name, part, sr=sr)
                            print(f"tmp-data: {tmp.name}")
                            # あなたの transcribe_with_path は Path だけ受け取る想定
                            result = transcribe_with_path(Path(tmp.name))
                            print(f"┗━ t━anscribe result: {result}")
                        await ws.send_json({"type": "partial", "text": result["text"]})
                elif (t:=msg.get("text")) is not None:
                    # 制御用メッセージ
                    if t == "flush":
                        # 残りをまとめて認識
                        if buf:
                            with tempfile.NamedTemporaryFile(suffix=".wav", dir="/data/tmp", delete=False) as tmp:
                                write_pcm16_wav(tmp.name, bytes(buf), sr=sr)
                                result = transcribe_with_path(Path(tmp.name))
                            await ws.send_json({"type": "partial", "text": result["text"]})
                            buf.clear()
                        await ws.send_json({"type": "done"})
                    # 他のテキストが来たら必要に応じて分岐

            elif t == "websocket.disconnect":
                break

    except WebSocketDisconnect as e:
        print(e)

        pass

    # デバッグ用
    except Exception as e:
        print(f"Error: {e}")
        # デバッグしやすいように返す（本番は詳細を隠す）
        try:
            await ws.send_json({"type": "error", "detail": str(e)})
        except Exception:
            await ws.close()