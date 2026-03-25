# 技術スタック

> 関連: [00_overview.md](./00_overview.md) | [01_architecture.md](./01_architecture.md) | [03_roadmap.md](./03_roadmap.md)

## 現行スタック

| レイヤー | 技術 | バージョン | 用途 |
|---|---|---|---|
| バックエンド | FastAPI | 0.111.0 | Web フレームワーク |
| バックエンド | Starlette | 0.37.2 | ASGI フレームワーク (FastAPI依存) |
| バックエンド | Uvicorn | 0.30.6 | ASGI サーバー |
| バックエンド | Python | 3.12+ | ランタイム |
| 音声認識 | OpenAI Whisper | latest | 文字起こしモデル **(→ Faster Whisper に移行予定)** |
| 音声認識 | PyTorch | latest (CPU) | 推論エンジン **(→ CTranslate2 に移行予定)** |
| 通信 | websockets | 12.0 | WebSocket ライブラリ |
| 設定管理 | pydantic-settings | latest | 環境変数ベース設定 |
| ファイル処理 | python-multipart | latest | マルチパートフォームデータ |
| フロントエンド | Vanilla JS | ES2020+ | UI・通信制御 |
| フロントエンド | Web Audio API | - | マイク入力・音声処理 |
| フロントエンド | AudioWorklet | - | リサンプリング・PCM変換 |
| インフラ | Docker | - | コンテナ化 |
| 音声処理 | ffmpeg | - | 音声コーデック (Whisper依存) |

## Phase 1 での変更: Faster Whisper 移行

### 変更前 → 変更後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| パッケージ | `openai-whisper` + `torch` | `faster-whisper` (CTranslate2) |
| 推論速度 | 基準 (1x) | 4〜8倍高速 |
| メモリ使用量 | 多い (PyTorch フル) | 大幅削減 (CTranslate2 最適化) |
| 量子化 | なし (fp32) | `int8` 対応 (CPU最適化) |
| GPU必要性 | medium以上で事実上必須 | **small まで CPU で十分** |

### 移行後の依存関係 (requirements.txt 想定)

```
fastapi==0.111.0
starlette==0.37.2
uvicorn[standard]==0.30.6
websockets==12.0
python-multipart
faster-whisper
pydantic-settings
```

**注**: `openai-whisper` と `torch` が不要になり、Docker イメージサイズも大幅削減される。

### 注意事項

- `websockets` は v12 を使用。v14 以降でプロトコル変更があるため `<14` の制約が必要
- `pyproject.toml` では `requires-python = ">=3.13"` だが、Dockerfile は `python:3.12` ベース (要統一)

## Whisper モデル (Faster Whisper, CPU int8)

| モデル | メモリ使用量 | 1秒音声の推論時間 | リアルタイム可否 | 備考 |
|---|---|---|---|---|
| tiny | ~0.5GB | ~0.1秒 | 余裕 | |
| base | ~0.5GB | ~0.2秒 | 余裕 | |
| **small** | **~1GB** | **~0.5秒** | **可能** | **Stage 1 推奨** |
| medium | ~3GB | ~1.5秒 | ギリギリ〜不可 | Stage 2 以降で検討 |
| large-v3 | ~6GB | ~4秒 | 不可 | Stage 3 (GPU) で使用 |

**Stage 1 の目標**: small (int8) モデルで CPU リアルタイム文字起こし (16GB RAM 自宅端末)

## インフラ構成の段階的移行

### Stage 1: 自宅端末 (現在の目標)

| 項目 | 値 |
|---|---|
| ハードウェア | 既存端末 (16GB RAM) |
| 推論エンジン | Faster Whisper (CTranslate2, CPU, int8) |
| モデル | small |
| 月額コスト | 電気代のみ (~500円) |
| 用途 | 開発・効果見極め |

### Stage 2: 外部 VPS (CPU)

| 項目 | 値 |
|---|---|
| 候補 | ConoHa 4GB (~1,860円/月) / Hetzner CPX31 (~1,730円/月) |
| 推論エンジン | Faster Whisper (CTranslate2, CPU, int8) |
| モデル | small → medium |
| 用途 | 外部公開・安定運用 |

### Stage 3: GPU VPS

| 項目 | 値 |
|---|---|
| 候補 | RunPod L4 ($0.39/hr) / GCP g2-standard-4 |
| 推論エンジン | Faster Whisper (CTranslate2, GPU, float16) |
| モデル | large-v3 |
| 用途 | 高精度推論・後処理バッチ (話者特定・感情認識・音声合成) |
| 運用 | オンデマンド (後処理時のみ起動) でコスト最適化 |

## 将来の技術検討

Phase 4-5 ([03_roadmap.md](./03_roadmap.md)) で検討が必要な技術。全て後処理前提で CPU でも実行可能。

| 用途 | 候補技術 | CPU実現性 | 検討ポイント |
|---|---|---|---|
| 話者特定 | pyannote.audio / resemblyzer | 中 (時間かかるが可能) | ライセンス確認が必要 |
| 感情認識 | SpeechBrain / Wav2Vec2 | 中 (バッチ処理) | 日本語対応モデルの有無 |
| トピック検出 | OpenAI API / ローカルLLM | 高 (テキストベース) | コスト vs ローカル実行 |
| 音声合成 | VOICEVOX / Style-Bert-VITS2 | 中 (事前生成) | 日本語特化・感情制御対応 |
| 声質変換 | RVC / so-vits-svc | 中 (バッチ変換) | 品質とCPU処理時間 |
| データベース | PostgreSQL / SQLite | - | 規模に応じて選定 |
| フロントエンド | React / Vue.js | - | Phase 2 でUI複雑化時に検討 |

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
