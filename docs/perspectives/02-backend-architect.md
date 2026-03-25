# バックエンドアーキテクト視点の分析

## 1. 全体アーキテクチャ

### 推奨: モジュラーモノリス → 段階的マイクロサービス化

Phase 1ではモジュラーモノリスとして内部をドメイン境界で分離し、Phase 2以降で重い処理(GPU推論系)だけをワーカーとして切り出す。

### リアルタイムパイプライン

```
Client (PCM16 via WebSocket)
  → [1] Audio Ingest (VAD付きバッファリング)
  → [2] Transcription (faster-whisper, リアルタイム)
  → [3] Fan-out (並列: Diarization, Emotion, Topic)
  → [4] Aggregator (マージ → DB永続化 → WS Push)
```

**重要な設計判断:** 文字起こし[2]だけがリアルタイム必須。[3]は非同期(数秒遅延許容)でタスクキュー経由。

## 2. データモデル

### DB: PostgreSQL + Redis + Object Storage (MinIO/S3)

主要テーブル:
- `users` — ユーザー
- `sessions` — 録音セッション (status: recording/processing/done)
- `utterances` (segments) — 発話セグメント (start_sec, end_sec, text, speaker_id, confidence)
- `speakers` — 話者 (label, embedding VECTOR(192), color)
- `emotions` — 感情分析結果 (primary_emotion, scores JSONB, arousal, valence)
- `topics` — トピック/タグ (name, start_sec, end_sec, source: auto/manual)
- `voice_conversions` — 音声変換結果 (character_voice, audio_path, status)

## 3. API設計

### REST
- `POST/GET/PATCH/DELETE /api/v1/sessions` — セッションCRUD
- `GET /api/v1/sessions/{id}/utterances` — 発話一覧
- `GET /api/v1/sessions/{id}/speakers` — 話者一覧
- `GET /api/v1/sessions/{id}/emotions` — 感情タイムライン
- `GET /api/v1/sessions/{id}/topics` — トピック一覧
- `POST /api/v1/utterances/{id}/convert` — 音声変換リクエスト

### WebSocket
- `WS /ws/transcribe/{session_id}`
- プロトコル: start → ready → binary frames → partial/final/speaker/emotion/topic → done

## 4. 非同期処理

### ARQ (Redis-based task queue)

- FastAPI + asyncio との親和性が高い
- Celeryより軽量
- GPU並列数に合わせて `max_jobs` を調整
- ワーカー起動時にモデルをプリロード

### 結果通知フロー

ARQ Worker完了 → Redis Pub/Sub → FastAPIバックグラウンドリスナー → WebSocket Push

## 5. 技術スタック追加

| 追加技術 | 用途 |
|---------|------|
| faster-whisper | Whisper置換 (4倍高速) |
| Silero VAD | 発話区間検出 |
| PostgreSQL 16 + pgvector | メタデータ + ベクトル検索 |
| SQLAlchemy 2.0 + Alembic | ORM + マイグレーション |
| ARQ | 非同期タスクキュー |
| Redis 7 | キャッシュ / PubSub / キュー |
| MinIO | オブジェクトストレージ |

## 6. 最重要改善点

1. `openai-whisper` → `faster-whisper` への置き換え
2. WebSocketハンドラでの同期ブロッキング解消 (`run_in_executor`)
3. 固定秒分割 → VADベース分割
