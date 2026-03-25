# システムアーキテクチャ

> 関連: [00_overview.md](./00_overview.md) | [04_tech_stack.md](./04_tech_stack.md)

## 全体構成

```
+------------------------------------------------------------------+
|                        CLIENT (Browser)                          |
|------------------------------------------------------------------|
|  HTML/CSS UI (MemoRec)                                           |
|  +-- index.html        メインアプリUI                             |
|  +-- audio_test.html   結合テスト用ページ                          |
|                                                                  |
|  JavaScript Audio Pipeline:                                      |
|  +-- Recorder          Web Audio API によるマイク入力              |
|  |   +-- AudioWorklet  リサンプリング (48kHz->16kHz) + PCM16変換   |
|  +-- WebsocketService  WebSocket通信制御 (未完成)                  |
+------------------------------------------------------------------+
                          |
          WebSocket & HTTP | TCP 8000
                          v
+------------------------------------------------------------------+
|                  SERVER (FastAPI / Python)                        |
|------------------------------------------------------------------|
|  FastAPI Application (main.py)                                   |
|  +-- REST Router (/v1)                                           |
|  |   +-- GET  /health           ヘルスチェック                     |
|  |   +-- POST /transcribe       ファイルアップロード文字起こし       |
|  |                                                                |
|  +-- WebSocket Router                                            |
|      +-- /ws/test               エコーテスト                      |
|      +-- /ws/test2              認証付きブロードキャスト            |
|      +-- /ws/transcribe         バイナリストリーミング (デモ)       |
|      +-- /ws/transcribe_audio   PCM16音声ストリーミング (本番)     |
|                                                                  |
|  Services:                                                       |
|  +-- WhisperService (whisper.py)                                 |
|      +-- モデル管理 (遅延ロード・シングルトン)                      |
|      +-- 文字起こし処理 (日本語最適化)                              |
|                                                                  |
|  Configuration:                                                  |
|  +-- Settings (config.py) - pydantic-settings ベース              |
+------------------------------------------------------------------+
                          |
                          | File I/O
                          v
+------------------------------------------------------------------+
|                     Storage & Models                             |
|------------------------------------------------------------------|
|  /cache/whisper/       Whisper モデルファイル                      |
|  /data/tmp/            一時WAVファイル                             |
|  /logs/                アプリケーションログ                         |
+------------------------------------------------------------------+
```

## 音声処理パイプライン

リアルタイムWebSocketストリーミングの処理フロー:

```
1. クライアント マイク入力
   |
2. AudioContext (ブラウザネイティブ, 通常 48kHz)
   |
3. AudioWorklet Processor
   +-- 線形補間リサンプリング (48kHz -> 16kHz)
   +-- Float32 -> PCM16LE 変換
   |
4. ArrayBuffer (50ms フレーム単位)
   |
5. WebSocket バイナリフレーム送信
   |
6. サーバー側バッファリング
   |
7. windowSec (デフォルト1秒) 単位でチャンク分割
   |
8. 一時 WAV ファイル生成
   |
9. OpenAI Whisper モデル推論
   |
10. JSON 文字起こし結果
   |
11. WebSocket JSON レスポンスとしてクライアントへ返送
```

## WebSocket プロトコル仕様

### `/ws/transcribe_audio` (メインエンドポイント)

```
Client -> Server: {"type": "start", "sampleRate": 16000, "language": "ja", "windowSec": 1}
Server -> Client: {"type": "ready"}

Client -> Server: [binary PCM16 frames]  (連続送信)

Server -> Client: {"type": "partial", "text": "..."}  (部分結果)

Client -> Server: "flush"  (テキスト, 残バッファ処理指示)

Server -> Client: {"type": "done"}  (完了通知)
```

## REST API 仕様

### `POST /v1/transcribe`

```
Request:  multipart/form-data (file フィールド)
Response: {"language": "ja", "duration": float, "text": "..."}
Error:    HTTP 500 {"detail": "transcription failed"}
```

### `GET /v1/health`

```
Response: {"status": "OK"}
```

## 設計パターン

| パターン | 適用箇所 | 説明 |
|---|---|---|
| 遅延ロード | WhisperService | モデルは初回使用時にロード、グローバルキャッシュ |
| ストリーミング | Audio Pipeline | クライアント50msフレーム、サーバー1秒チャンク |
| プロセス分離 | AudioWorklet | 音声処理は別スレッドで実行 |
| ゼロコピー転送 | Recorder -> WS | Transferable objects によるArrayBuffer受け渡し |
| コンテナ化 | Docker | ホットリロード対応の開発環境 |

## ファイル構成

```
server/
  main.py                  FastAPI アプリケーション初期化
  core/config.py           設定管理 (pydantic-settings)
  api/routers.py           REST APIルーター
  api/router_ws.py         WebSocketルーター
  services/whisper.py      Whisper文字起こしサービス
  .env.example             環境変数テンプレート

client/
  index.html               メインアプリUI
  audio_test.html          結合テストページ
  audio/recorder.js        Recorder クラス
  audio/recorder.worklet.js AudioWorklet プロセッサ
  src/main.js              エントリポイント (スタブ)
  src/services/websocket/ws.js WebsocketService (未完成)

work/
  test1.html               WebSocket エコーテスト
  test2.html               WebSocket 認証テスト
```
