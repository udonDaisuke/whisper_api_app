# 現在の実装状況

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

### BUG-003: デバッグ用 `print` 文の残存

- **ファイル**: `server/api/router_ws.py`, `server/services/whisper.py`
- **内容**: 開発中の `print()` 文が多数残っている
- **影響**: 本番環境でのログ汚染、パフォーマンスへの微小な影響
- **修正方針**: `logging` モジュールに置き換え (ロードマップ Phase 1 参照: [03_roadmap.md](./03_roadmap.md))

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

## 完成度サマリ

| コンポーネント | 完成度 | 説明 |
|---|---|---|
| バックエンド | 約 90% | REST APIにバグあり、WebSocketは動作 |
| フロントエンド | 約 40% | 音声キャプチャは動作、UIとWSサービスが未完成 |
| E2E結合 | 動作確認済み | `audio_test.html` 経由で文字起こし可能 |
| 本番対応 | 未対応 | エラーハンドリング・ログ・認証が不足 |
