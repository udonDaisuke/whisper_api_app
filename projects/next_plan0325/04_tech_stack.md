# 技術スタック

> 関連: [00_overview.md](./00_overview.md) | [01_architecture.md](./01_architecture.md)

## 現行スタック

| レイヤー | 技術 | バージョン | 用途 |
|---|---|---|---|
| バックエンド | FastAPI | 0.111.0 | Web フレームワーク |
| バックエンド | Starlette | 0.37.2 | ASGI フレームワーク (FastAPI依存) |
| バックエンド | Uvicorn | 0.30.6 | ASGI サーバー |
| バックエンド | Python | 3.12+ | ランタイム |
| 音声認識 | OpenAI Whisper | latest | 文字起こしモデル |
| 音声認識 | PyTorch | latest (CPU) | 推論エンジン |
| 通信 | websockets | 12.0 | WebSocket ライブラリ |
| 設定管理 | pydantic-settings | latest | 環境変数ベース設定 |
| ファイル処理 | python-multipart | latest | マルチパートフォームデータ |
| フロントエンド | Vanilla JS | ES2020+ | UI・通信制御 |
| フロントエンド | Web Audio API | - | マイク入力・音声処理 |
| フロントエンド | AudioWorklet | - | リサンプリング・PCM変換 |
| インフラ | Docker | - | コンテナ化 |
| 音声処理 | ffmpeg | - | 音声コーデック (Whisper依存) |

## 依存関係 (requirements.txt)

```
fastapi==0.111.0
starlette==0.37.2
uvicorn[standard]==0.30.6
websockets==12.0
python-multipart
openai-whisper
torch (CPU版, PyTorch公式wheelから)
pydantic-settings
```

### 注意事項

- `websockets` は v12 を使用。v14 以降でプロトコル変更があるため `<14` の制約が必要
- `torch` は CPU 版を使用。GPU 対応は Phase 4 以降で検討 (参照: [03_roadmap.md](./03_roadmap.md))
- `pyproject.toml` では `requires-python = ">=3.13"` だが、Dockerfile は `python:3.12` ベース (要統一)

## Whisper モデル

| モデル | パラメータ数 | メモリ使用量 | 精度 | 速度 |
|---|---|---|---|---|
| tiny | 39M | ~1GB | 低 | 最速 |
| base | 74M | ~1GB | やや低 | 速い |
| small | 244M | ~2GB | 中 | 普通 |
| medium | 769M | ~5GB | 高 | 遅い |
| large | 1550M | ~10GB | 最高 | 最遅 |

現在は `tiny` モデルをキャッシュ済み。`.env` で `WHISPER_MODEL` を変更可能。

## 将来の技術検討

Phase 4-5 ([03_roadmap.md](./03_roadmap.md)) で検討が必要な技術:

| 用途 | 候補技術 | 検討ポイント |
|---|---|---|
| 高速文字起こし | Faster Whisper (CTranslate2) | Whisperの4-8倍高速、メモリ効率向上 |
| 話者特定 | pyannote.audio | ライセンス確認が必要 (研究目的は無料) |
| 感情認識 | SpeechBrain / Wav2Vec2 | 日本語対応モデルの有無を調査 |
| トピック検出 | OpenAI API / ローカルLLM | コスト vs リアルタイム性 |
| 音声合成 | VOICEVOX / Style-Bert-VITS2 | 日本語特化・感情制御対応 |
| 声質変換 | RVC / so-vits-svc | リアルタイム変換の可否 |
| データベース | PostgreSQL / SQLite | 規模に応じて選定 |
| フロントエンド | React / Vue.js | Phase 2 でUI複雑化時に検討 |

## Docker 構成

### Dockerfile.dev

```dockerfile
FROM python:3.12
RUN apt-get update && apt-get install -y ffmpeg
ENV XDG_CACHE_HOME=/cache
WORKDIR /server
COPY requirements.txt .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### ボリュームマウント (run.sh)

| ホスト | コンテナ | 用途 |
|---|---|---|
| `./server` | `/server` | ソースコード (ホットリロード) |
| `./cache` | `/cache` | Whisper モデルキャッシュ |
| `./var/data` | `/data` | 一時ファイル |
| `./var/logs` | `/logs` | ログファイル |

### ネットワーク

- ホストポート: 8000
- コンテナポート: 8000
