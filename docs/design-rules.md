# MemoRec 設計ルール

> 最終更新: 2026-03-26
> 関連: [architecture.md](./architecture.md)

このドキュメントは実装時に守るべき設計ルールを定める。
レビュー時の判断基準・AI エージェントへの指示・新メンバーへの指針として使用する。

---

## レイヤールール

### RULE-L1: API ルーターはサービス層にのみ依存する

API ルーター (`api/routers/`, `api/ws/`) から直接 Repository・DB・Model を import してはならない。
必ず Service 層を経由し、Service 層は DI (`api/deps.py`) で注入する。

```
# NG
from infra.repositories.session_repo import SQLiteSessionRepository

# OK
def get_sessions(service: SessionService = Depends(get_session_service)):
    ...
```

### RULE-L2: サービス層はインフラを知らない

Service 層 (`services/`) は具体的な DB アダプター・ファイルパス・HTTP ライブラリを直接参照しない。
インフラへのアクセスは必ず Repository または Store インタフェース経由とする。

### RULE-L3: Pipeline ステップは副作用を持たない

`PipelineStep` の `process(context, input)` メソッドは純粋な変換処理のみ行い、DB 書き込み・外部 HTTP 呼び出し・ファイル IO を直接実行してはならない。
副作用が必要な場合は `context` にイベントを積み、Orchestrator が実行する。

### RULE-L4: Plugin は ComputeAdapter を直接参照しない

`ModelPlugin.infer()` は入力データのみを受け取り、デバイス指定・量子化設定は ComputeAdapter が管理する。
Plugin は `compute_adapter.infer(model_handle, input)` を呼ぶだけでよい。

---

## 命名規則

### RULE-N1: インタフェースと実装の命名

| 種別 | パターン | 例 |
|------|---------|-----|
| Repository インタフェース | `{Entity}Repository` | `SessionRepository` |
| Repository 実装 | `{DB}{Entity}Repository` | `SQLiteSessionRepository` |
| Plugin インタフェース | `ModelPlugin` (Protocol) | - |
| Plugin 実装 | `{Model}Plugin` | `FasterWhisperPlugin` |
| Adapter インタフェース | `{Type}Adapter` | `ComputeAdapter`, `JobQueue` |
| Adapter 実装 | `{Backend}{Type}Adapter` | `CPUComputeAdapter`, `ARQJobQueue` |

### RULE-N2: WebSocket メッセージタイプ

クライアント送信: 動詞 (`start`, `control`, `ping`)
サーバー送信: 名詞または状態 (`ready`, `partial`, `final`, `error`, `job_update`, `pong`)

### RULE-N3: 設定キーの命名

環境変数は `SCREAMING_SNAKE_CASE`。Stage 切り替えに関わる設定キーは以下に統一する。

```
COMPUTE_DEVICE=cpu|cuda
COMPUTE_TYPE=int8|float16
DB_BACKEND=sqlite|postgres
JOB_QUEUE_BACKEND=sync|arq
WHISPER_MODEL=tiny|base|small|medium|large-v3
```

---

## 拡張ルール

### RULE-E1: 新しい AI モデルは Plugin として実装する

新モデルを追加する際は `ModelPlugin` インタフェースを実装し、`PluginRegistry` に登録するだけでよい。
既存コード (PipelineOrchestrator・Service 層) を変更してはならない。

### RULE-E2: 新しい後処理ステップは PipelineStep として実装する

後処理機能 (新しい分析ステップ) を追加する際は `PipelineStep` を実装し、`PostProcessingSaga` のステップ列に追加するだけでよい。
Saga の骨格コードを変更してはならない。

### RULE-E3: 新しいストレージバックエンドはアダプターとして実装する

S3 対応・新 DB 対応は既存のインタフェースを実装する新アダプターとして追加する。
設定値 (`settings.STORAGE_BACKEND`) で切り替え可能にする。

---

## Stage 移行ルール

### RULE-S1: Stage 1 実装はインタフェースを省略しない

Stage 1 でシンプル化するのは「具体実装の内容」のみ。
インタフェース定義・DI 設計・Repository パターンは Stage 1 から必ず実装する。
これを怠ると Stage 2 移行時に全体書き直しになる。

### RULE-S2: Stage 切り替えはコード変更なく環境変数のみで行う

Stage 2 移行 (SQLite → PostgreSQL, SynchronousQueue → ARQQueue) はコード変更ゼロ・環境変数変更のみで完了できること。
このルールに違反する設計変更はリジェクトする。

### RULE-S3: Stage 3 GPU 移行は ComputeAdapter の差し替えのみで行う

`COMPUTE_DEVICE=cuda` の環境変数変更と `GPUAdapter` の起動設定追加のみで GPU 推論に切り替わること。
Plugin・Service 層に CUDA 固有コードを書いてはならない。

---

## コード品質ルール

### RULE-Q1: print 文を使用しない

`print()` は禁止。構造化ロギング (`logging` モジュール) を使用する。
ログレベルは `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` を適切に使い分ける。

```python
# NG
print(f"transcription result: {text}")

# OK
logger.info("transcription_complete", extra={"text_length": len(text), "session_id": ctx.session_id})
```

### RULE-Q2: 一時ファイルは必ず finally で削除する

WAV 一時ファイルなど、処理後に不要なファイルは `try/finally` ブロックで確実に削除する。

```python
# OK
try:
    wav_path = audio_store.write_temp(pcm_data)
    result = model.transcribe(wav_path)
finally:
    audio_store.delete_temp(wav_path)
```

### RULE-Q3: 設定値をハードコードしない

サンプルレート・モデル名・タイムアウト値・言語設定などをコード内にリテラルで書いてはならない。
すべて `settings.*` から参照し、`.env.example` に記載する。

```python
# NG
model = FasterWhisper("small", compute_type="int8")

# OK
model = FasterWhisper(settings.WHISPER_MODEL, compute_type=settings.COMPUTE_TYPE)
```

### RULE-Q4: WebSocket エンドポイントは認証なしで公開しない

`/ws/transcribe` など音声データを扱う WS エンドポイントは必ず認証チェックを行う。
`Authorization` ヘッダーまたはクエリパラメータのトークンを検証する。

### RULE-Q5: エラーはコードで分類する

例外・エラーレスポンスは `core/errors.py` に定義したカスタム例外クラスを使用し、エラーコード文字列 (`BUFFER_OVERFLOW`, `AUTH_FAILED` 等) で分類する。
汎用の `Exception` を直接 raise しない。

---

## テストルール

### RULE-T1: Service 層のテストは InMemory Repository を使用する

Service 単体テストは実 DB に依存しない。`InMemorySessionRepository` 等を DI で注入し、高速・独立したテストを維持する。

### RULE-T2: Plugin のテストはモックデータで実行する

`FasterWhisperPlugin` 等のテストは実モデルファイルに依存しない。
モックの音声データ・モックの推論結果を使用し、CI 環境で常に実行可能にする。

### RULE-T3: Pipeline ステップのテストは単体で行う

`PipelineStep.process()` はステップ単体でテスト可能な設計にする。
Orchestrator 全体を通したテストは Integration Test として分離する。

---

## ADR (Architecture Decision Records)

設計上の重要な意思決定は `docs/adr/` に記録する。
変更・撤回する際は既存 ADR をステータス更新し、新 ADR を追加する。

| ファイル | 決定内容 |
|---------|---------|
| [adr/001-faster-whisper.md](./adr/001-faster-whisper.md) | OpenAI Whisper → Faster Whisper (CTranslate2) 移行 |
| [adr/002-plugin-registry.md](./adr/002-plugin-registry.md) | Plugin Registry パターンの採用 |
| [adr/003-saga-pattern.md](./adr/003-saga-pattern.md) | 後処理パイプラインへの Saga パターン採用 |
