# 現在の実装状況

> 最終更新: 2026-03-26 (Issue #3 コードベース分析 + Issue #9 BUG-003 修正反映)
> 関連: [00_overview.md](./00_overview.md) | [01_architecture.md](./01_architecture.md)

## 実装済み機能

### バックエンド (FastAPI)

| 機能 | エンドポイント | 状態 | 備考 |
|---|---|---|---|
| ヘルスチェック | `GET /v1/health` | 実装済み | |
| ファイルアップロード文字起こし | `POST /v1/transcribe` | バグあり | `UPLOAD_CHUNK_BYTES` 未定義 |
| WebSocket エコーテスト | `/ws/test` | 実装済み | |
| WebSocket 認証テスト | `/ws/test2` | 実装済み | Cookie/トークン認証 |
| WebSocket 文字起こし (基本) | `/ws/transcribe` | 実装済み | デモレベル |
| WebSocket 文字起こし (ストリーミング) | `/ws/transcribe_audio` | 実装済み | コア機能 |

### フロントエンド (Vanilla JS)

| 機能 | 状態 | 備考 |
|---|---|---|
| マイク音声キャプチャ (Web Audio API) | 実装済み | `recorder.js` |
| AudioWorklet 音声処理 | 実装済み | リサンプリング + PCM16変換 |
| WebSocket 音声ストリーミング送信 | 実装済み | `audio_test.html` で動作確認済み |
| WebsocketService クラス | 未完成 | `ws.js` はスケルトンのみ |
| メインアプリUI | 未完成 | `index.html` はレイアウトのみ |
| `main.js` エントリポイント | 未実装 | `console.log("test")` のみ |

### インフラ

| 機能 | 状態 | 備考 |
|---|---|---|
| Docker 開発環境 | 実装済み | ホットリロード対応 |
| `run.sh` オーケストレーション | 実装済み | build/up/down/logs/shell |
| Whisper モデルキャッシュ永続化 | 実装済み | `/cache` ボリュームマウント |

## 既知バグ・問題

### BUG-001: `UPLOAD_CHUNK_BYTES` 未定義

- **ファイル**: `server/api/routers.py`
- **内容**: `settings.UPLOAD_CHUNK_BYTES` が参照されているが、`config.py` に定義がない
- **影響**: `POST /v1/transcribe` 呼び出し時に `AttributeError` でクラッシュ
- **修正方針**: `config.py` の `Settings` クラスに `UPLOAD_CHUNK_BYTES: int = 1024 * 1024` を追加

### BUG-002: `.env` ファイルパス誤り

- **ファイル**: `server/core/config.py`
- **内容**: `env_file` が `"./env"` となっている (正しくは `".env"`)
- **影響**: 環境変数ファイルが読み込まれない
- **修正方針**: `env_file = ".env"` に修正

### BUG-003: デバッグ用 `print` 文の残存 ✅ **修正済み (PR #37)**

- **ファイル**: `server/api/router_ws.py`, `server/services/whisper.py`
- **内容**: 開発中の `print()` 文が多数残っていた
- **影響**: 本番環境でのログ汚染、パフォーマンスへの微小な影響
- **対応**: `server/core/logging.py` に JSON 構造化ロギングを実装し、全 `print()` を `logging` モジュールに置換済み

### BUG-004: 一時ファイル未クリーンアップ

- **ファイル**: `server/api/router_ws.py`
- **内容**: `/data/tmp` に生成される WAV ファイルが削除されない
- **影響**: ディスク容量の圧迫
- **修正方針**: 処理完了後に一時ファイルを削除する finally ブロック追加、または定期クリーンアップ機構の導入

### BUG-005: ハードコードされた日本語設定

- **ファイル**: `server/services/whisper.py`
- **内容**: 言語パラメータが `"ja"` で固定されている
- **影響**: 日本語以外の音声認識ができない
- **修正方針**: WebSocket 開始メッセージの `language` パラメータをサービス層まで伝搬させる

### BUG-006: `WebsocketService` の `this.opts` 参照ミス

- **ファイル**: `client/src/services/websocket/ws.js`
- **内容**: コンストラクタでは `this.options` に設定を格納しているが、バリデーション箇所で `this.opts.url` / `this.opts.wsCtor` を参照している
- **影響**: `new WebsocketService(...)` 呼び出し時に即座に `TypeError: Cannot read properties of undefined` でクラッシュする
- **修正方針**: バリデーション行を `this.options.url` / `this.options.wsCtor` に修正する

### BUG-007: `settings.XDG_CACHE_HOME` 未定義

- **ファイル**: `server/main.py`
- **内容**: `settings.XDG_CACHE_HOME` が参照されているが、`server/core/config.py` の `Settings` クラスに定義がない
- **影響**: アプリ起動時に `AttributeError: 'Settings' object has no attribute 'XDG_CACHE_HOME'` でクラッシュ
- **修正方針**: `config.py` の `Settings` クラスに `XDG_CACHE_HOME: str = "/cache"` を追加する

## 完成度サマリ

| コンポーネント | 完成度 | 説明 |
|---|---|---|
| バックエンド | 約 75% | BUG-001/002/007 により起動自体が失敗する。WebSocket は動作実績あり |
| フロントエンド | 約 30% | 音声キャプチャは動作。ws.js は BUG-006 でクラッシュ。main.js 未実装 |
| E2E 結合 | 条件付き動作 | `audio_test.html` 経由で文字起こし可能 (バグ回避時) |
| 本番対応 | 未対応 | エラーハンドリング・認証が不足。ロギングは整備済み (BUG-003 修正) |

## バグ優先度まとめ

| バグ | 優先度 | 状態 | 影響 |
|---|---|---|---|
| BUG-007: `XDG_CACHE_HOME` 未定義 | **最高** | 未修正 | 起動クラッシュ |
| BUG-001: `UPLOAD_CHUNK_BYTES` 未定義 | 高 | 未修正 | REST API クラッシュ |
| BUG-002: `.env` パス誤り | 高 | 未修正 | 環境変数読み込み失敗 |
| BUG-006: `ws.js` `this.opts` 参照ミス | 高 | 未修正 | フロントエンド WS クラッシュ |
| BUG-003: `print()` 残存 | 高 | **修正済み** (PR #37) | ログ汚染 |
| BUG-004: 一時ファイル未クリーンアップ | 中 | 未修正 | ディスク圧迫 |
| BUG-005: 言語パラメータ固定 | 中 | 未修正 | 多言語非対応 |
