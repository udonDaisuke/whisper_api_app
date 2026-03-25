# MemoRec システムアーキテクチャ

> 最終更新: 2026-03-26
> ステータス: 設計確定 (Phase 1 実装着手前)
> 関連: [design-rules.md](./design-rules.md) | [roadmap/current/03_roadmap.md](../roadmap/current/03_roadmap.md)

---

## 設計思想

段階的スケール (Stage 1→3) と機能追加 (Phase 1→5) の両方に対応するため、以下を設計の軸とする。

1. **段階透過**: ビジネスロジックはインフラ Stage (CPU/GPU/VPS) を知らない
2. **プラグイン拡張**: 新しい AI モデルをコア変更なしに追加できる
3. **リアルタイムとバッチの明確な分離**: WebSocket パイプラインとジョブキューを独立させる
4. **段階的複雑化**: Stage 1 は同期シンプル、Stage 2+ でキュー追加、Stage 3 で GPU アダプター追加

---

## レイヤードアーキテクチャ

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                        PRESENTATION LAYER (Browser)                             ║
║                                                                                  ║
║  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────┐   ║
║  │   AudioPipeline  │  │   TranscriptUI   │  │      SessionManager          │   ║
║  │ (Worklet/PCM16)  │  │  (結果表示・検索)  │  │  (状態管理・認証トークン)    │   ║
║  └────────┬─────────┘  └────────┬─────────┘  └──────────────┬───────────────┘   ║
║           │                     │                            │                   ║
║  ┌────────▼─────────────────────▼────────────────────────────▼───────────────┐   ║
║  │                    ProtocolGateway (client-side)                           │   ║
║  │  WebSocketService (ws-service.js)  │  HttpApiClient (http-client.js)      │   ║
║  └─────────────────────────────────────────────────────────────────────────┬─┘   ║
╚═════════════════════════════════════════════════════════════════════════════╪═════╝
                                  WebSocket / HTTPS                           │
══════════════════════════════════════════════════════════════════════════════╪══════
╔═════════════════════════════════════════════════════════════════════════════▼═════╗
║                         API GATEWAY LAYER (FastAPI)                              ║
║                                                                                   ║
║  ┌─────────────────────┐  ┌──────────────────────┐  ┌─────────────────────────┐  ║
║  │  REST Router (/v1)  │  │   WS Router (/ws)    │  │      Middleware          │  ║
║  │  - POST /sessions   │  │  - /ws/transcribe    │  │  - Auth/JWT             │  ║
║  │  - GET  /sessions   │  │  - /ws/status        │  │  - RateLimit            │  ║
║  │  - POST /jobs       │  │                      │  │  - StructuredLogging    │  ║
║  │  - GET  /health     │  │                      │  │  - CORS                 │  ║
║  └──────────┬──────────┘  └──────────┬───────────┘  └─────────────────────────┘  ║
╚═════════════│═════════════════════════│══════════════════════════════════════════╝
              │                         │
══════════════│═════════════════════════│══════════════════════════════════════════
╔═════════════▼═════════════════════════▼══════════════════════════════════════════╗
║                              SERVICE LAYER                                        ║
║                                                                                   ║
║  ┌───────────────────────┐  ┌────────────────────────┐  ┌────────────────────┐   ║
║  │  RTTranscriptionSvc   │  │     SessionService     │  │  PostProcessSvc    │   ║
║  │ (リアルタイム文字起こし)│  │  (セッション・CRUD)    │  │  (後処理ジョブ管理) │   ║
║  └──────────┬────────────┘  └────────────┬───────────┘  └──────────┬─────────┘   ║
║             │                            │                          │             ║
║  ┌──────────▼────────────────────────────▼──────────────────────────▼──────────┐  ║
║  │                        PipelineOrchestrator                                  │  ║
║  │  RT:    PCMChunk → [VADGate] → TranscriptionStep → ResultEmitter            │  ║
║  │  Batch: SessionID → LoadAudio → [Diarize] → [Emotion] → [Topic] → Persist  │  ║
║  └──────────────────────────────────┬───────────────────────────────────────┘   ║
╚══════════════════════════════════════│═══════════════════════════════════════════╝
                                       │
══════════════════════════════════════│═══════════════════════════════════════════
╔══════════════════════════════════════▼═══════════════════════════════════════════╗
║                         PLUGIN / COMPUTE LAYER                                   ║
║                                                                                   ║
║  ┌─────────────────────────────────────────────────────────────────────────┐     ║
║  │                          PluginRegistry                                  │     ║
║  │  ┌─────────────────┐  ┌────────────────────┐  ┌─────────────────────┐  │     ║
║  │  │ FasterWhisper   │  │  PyannotePlugin    │  │  VOICEVOXPlugin     │  │     ║
║  │  │ Plugin (P1)     │  │  (diarization, P4) │  │  (TTS, P5)          │  │     ║
║  │  └────────┬────────┘  └─────────┬──────────┘  └──────────┬──────────┘  │     ║
║  └───────────│──────────────────────│────────────────────────│─────────────┘     ║
║              │          ComputeAdapter                        │                   ║
║  ┌───────────▼──────────────────────▼─────────────────────────▼──────────────┐   ║
║  │  CPUAdapter (int8/CTranslate2)   │   GPUAdapter (float16/CUDA, Stage 3)  │   ║
║  └─────────────────────────────────────────────────────────────────────────┘    ║
╚═════════════════════════════════════════════════════════════════════════════════╝
                                       │
══════════════════════════════════════│═══════════════════════════════════════════
╔══════════════════════════════════════▼═══════════════════════════════════════════╗
║                    INFRASTRUCTURE / STORAGE LAYER                                ║
║                                                                                   ║
║  ┌────────────────────────┐  ┌────────────────────────┐  ┌──────────────────┐   ║
║  │   SessionRepository    │  │  TranscriptRepository  │  │  JobRepository   │   ║
║  │  SQLite / PostgreSQL   │  │  SQLite / PostgreSQL   │  │  SQLite / PG     │   ║
║  └────────────────────────┘  └────────────────────────┘  └──────────────────┘   ║
║                                                                                   ║
║  ┌────────────────────────┐  ┌────────────────────────┐  ┌──────────────────┐   ║
║  │   AudioFileStore       │  │   ModelCacheStore      │  │  JobQueue        │   ║
║  │  (local FS → S3)       │  │  (/cache/whisper/)     │  │  Sync → ARQ      │   ║
║  └────────────────────────┘  └────────────────────────┘  └──────────────────┘   ║
╚═════════════════════════════════════════════════════════════════════════════════╝
```

---

## 主要設計パターン

### Pipeline Pattern
**適用**: `PipelineOrchestrator`

各処理を `PipelineStep` インタフェースとして実装し、Orchestrator がステップ列をチェーンとして呼び出す。ステップの追加・削除・入れ替えがコア変更なしに行える。

- RT パイプライン: `PCMChunk → [VADGate] → TranscriptionStep → ResultEmitter`
- バッチパイプライン: `LoadAudio → DiarizationStep → EmotionStep → TopicStep → PersistStep`

### Adapter Pattern
**適用 1 — ComputeAdapter**: CPU/GPU の推論実装を共通インタフェースで隠蔽する。環境変数 `COMPUTE_DEVICE=cuda` の切り替えのみで GPU に移行できる。

**適用 2 — StorageAdapter**: `settings.DB_BACKEND` の切り替えで SQLite → PostgreSQL が完結する。

**適用 3 — JobQueueAdapter**: `SynchronousQueue` → `ARQQueue` の差し替えをインタフェース越しに行う。

### Strategy Pattern
**適用**: TranscriptionStep 内の `TranscriptionStrategy`

`FasterWhisperStrategy` を基本とし、将来的に `WhisperCppStrategy` や外部 API フォールバックを差し込める。

### Saga Pattern
**適用**: `PostProcessingSaga`

話者分離 → 感情認識 → トピック検出 → 永続化の各ステップが独立したトランザクションを構成する。ステップ失敗時は定義済みの補償アクションを逆順実行し、リカバリを保証する。

### Repository Pattern
**適用**: `SessionRepository`, `TranscriptRepository`, `JobRepository`

インフラ詳細をサービス層から分離する。テスト時は `InMemoryRepository` を DI で注入し、DB 不要の高速テストを実現する。

### Plugin Registry
**適用**: `PluginRegistry`

起動時に設定に基づいてプラグインをロードする。`registry.get(capability="transcribe")` で最適プラグインを返し、A/B テスト (モデル比較) にも対応できる拡張点を持つ。

---

## WebSocket プロトコル仕様

### メッセージエンベロープ (全メッセージ共通)

```json
{
  "v":    1,
  "type": "<message_type>",
  "seq":  42,
  "ts":   1711234567.890,
  "sid":  "sess_abc123"
}
```

### Client → Server

| type | 説明 | Phase |
|------|------|-------|
| `start` | セッション開始 (sampleRate, language, windowSec, features) | P1 |
| `control` | 制御 (action: flush \| pause \| resume \| abort) | P1 |
| `ping` | キープアライブ | P2 |

### Server → Client

| type | 説明 | Phase |
|------|------|-------|
| `ready` | セッション受け入れ (sid, model, capabilities) | P1 |
| `partial` | 部分認識結果 (text, startMs, endMs) | P1 |
| `final` | 確定認識結果 (text, segments) | P1 |
| `job_update` | 後処理ジョブ進捗 (jobId, step, status, progress) | P4 |
| `error` | エラー通知 (code, message, fatal) | P1 |
| `pong` | キープアライブ応答 | P2 |

---

## Stage 別の構成差分

| 要素 | Stage 1 (自宅端末) | Stage 2 (VPS+Queue) | Stage 3 (GPU) |
|------|-------------------|---------------------|---------------|
| ComputeAdapter | CPUAdapter / int8 | CPUAdapter / int8 | GPUAdapter / float16 |
| Whisper モデル | small | small → medium | large-v3 |
| JobQueue | SynchronousQueue | ARQQueue (Redis) | Priority + RunPod API |
| Database | SQLite | PostgreSQL | PostgreSQL |
| AudioFileStore | ローカル FS | ローカル FS | ローカル FS → S3 検討 |
| 認証 | Static Token | JWT + Refresh | JWT + Refresh |
| Worker | なし | ARQ Worker コンテナ | ARQ Worker + GPU Worker |

---

## ディレクトリ構成 (Phase 1-5 完了後の目標形)

```
server/
├── main.py
├── api/
│   ├── deps.py
│   ├── routers/
│   │   ├── health.py
│   │   ├── sessions.py
│   │   ├── transcripts.py
│   │   └── jobs.py
│   ├── ws/
│   │   ├── transcribe.py
│   │   └── status.py
│   └── schemas/
│       ├── ws_message.py
│       ├── session.py
│       ├── transcript.py
│       └── job.py
├── core/
│   ├── config.py
│   ├── logging.py
│   ├── auth.py
│   ├── errors.py
│   └── context.py
├── services/
│   ├── rt_transcription.py
│   ├── session_service.py
│   └── post_process_service.py
├── pipeline/
│   ├── orchestrator.py
│   ├── steps/
│   │   ├── base.py
│   │   ├── vad_gate.py         (Phase 2)
│   │   ├── transcription.py
│   │   ├── diarization.py      (Phase 4)
│   │   ├── emotion.py          (Phase 4)
│   │   ├── topic.py            (Phase 4)
│   │   ├── tts.py              (Phase 5)
│   │   └── voice_convert.py    (Phase 5)
│   └── saga/
│       └── post_process_saga.py
├── plugins/
│   ├── registry.py
│   ├── base.py
│   ├── transcribe/faster_whisper.py
│   ├── diarize/pyannote.py     (Phase 4)
│   ├── emotion/speechbrain.py  (Phase 4)
│   ├── tts/voicevox.py         (Phase 5)
│   └── vc/rvc.py               (Phase 5)
├── compute/
│   ├── base.py
│   ├── cpu.py
│   └── gpu.py                  (Phase 5)
└── infra/
    ├── db/
    │   ├── base.py
    │   ├── sqlite.py
    │   └── postgres.py         (Phase 3)
    ├── repositories/
    │   ├── base.py
    │   ├── session_repo.py
    │   ├── transcript_repo.py
    │   └── job_repo.py
    ├── stores/
    │   ├── audio_file_store.py
    │   └── model_cache_store.py
    └── queue/
        ├── base.py
        ├── sync_queue.py
        └── arq_queue.py        (Phase 4/Stage 2)

client/
├── index.html
├── audio/
│   ├── recorder.js
│   └── recorder.worklet.js
└── src/
    ├── main.js
    ├── session-manager.js
    ├── services/
    │   ├── ws-service.js
    │   └── http-client.js
    ├── ui/
    │   ├── transcript-view.js
    │   ├── session-list.js     (Phase 3)
    │   └── job-status.js       (Phase 4)
    └── protocol/
        └── message-schema.js

docs/
├── architecture.md             (このファイル)
├── design-rules.md
└── adr/
    ├── 001-faster-whisper.md
    ├── 002-plugin-registry.md
    └── 003-saga-pattern.md
```

---

## 関連ドキュメント

| ドキュメント | 内容 |
|---|---|
| [design-rules.md](./design-rules.md) | 実装時の設計ルール・禁止事項 |
| [adr/001-faster-whisper.md](./adr/001-faster-whisper.md) | Faster Whisper 移行の意思決定記録 |
| [adr/002-plugin-registry.md](./adr/002-plugin-registry.md) | Plugin Registry 採用の意思決定記録 |
| [adr/003-saga-pattern.md](./adr/003-saga-pattern.md) | Saga Pattern 採用の意思決定記録 |
| [roadmap/current/03_roadmap.md](../roadmap/current/03_roadmap.md) | 開発ロードマップ・フェーズ計画 |
