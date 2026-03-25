# MemoRec コンセプト & ロードマップ — 多角的議論の統合結果

> **本ドキュメントは、5名のエージェント（プロダクトマネージャー / バックエンドアーキテクト / ML/AIエンジニア / フロントエンド・UXデザイナー / DevOps・インフラエンジニア）による独立分析を統合し、最終的な落としどころをまとめたものである。**

---

## 1. プロダクトコンセプト（全員合意）

### MemoRec とは

**「録るだけで、わかる。探せる。活かせる。」**

MemoRecは、ブラウザからリアルタイムで音声を文字起こしし、話者・感情・トピックといったメタデータを自動付与する**音声インテリジェンスプラットフォーム**である。最終的には音声そのものを別キャラクターの声に変換する Voice Conversion まで包含し、**音声データから最大限の価値を引き出す**ことを目指す。

### 最大の差別化: ローカルファースト

| 観点 | MemoRec | 競合 (Otter.ai / Notta / CLOVA Note) |
|------|---------|--------------------------------------|
| 実行環境 | **ローカル / セルフホスト** | クラウドのみ |
| データ主権 | **音声が外部に出ない** | 外部サーバーへ送信 |
| 感情分析 | **対応 (Phase 3)** | 非対応 |
| Voice Conversion | **対応 (Phase 4)** | 非対応 |
| カスタマイズ性 | **OSS / 拡張可能** | クローズド |

> **全員の見解が一致**: ローカル実行 + 感情分析 + Voice Conversion の組み合わせは既存競合に存在しない独自ポジションである。

---

## 2. 議論のポイントと合意形成

### 2.1 フロントエンド技術選定

| 提案者 | 推奨 | 理由 |
|--------|------|------|
| PM | React / Next.js | エコシステムが大きく人材確保が容易 |
| UXデザイナー | **Svelte + Vite** | リアルタイム更新に最適、バンドル軽量、Vanilla JSからの移行コスト最小 |

**落としどころ: Svelte + Vite + Tailwind CSS**

- 個人開発プロジェクトであり、Svelteの軽量さとリアクティビティの自然さが最も合致する
- AudioWorklet等の既存Vanilla JS資産をそのまま流用できる
- Reactはチーム開発で活きるが、現段階では過剰

### 2.2 Whisperモデル選定

| 提案者 | 推奨モデル |
|--------|-----------|
| ML/AIエンジニア | **faster-whisper large-v3 (INT8)** + kotoba-whisper (日本語特化) |
| バックエンドアーキテクト | **faster-whisper** (openai-whisperから置換必須) |
| DevOps | faster-whisper (同GPU予算でより高性能) |

**落としどころ: faster-whisper への即時移行**（全員一致）

| 項目 | 現状 (openai-whisper tiny) | 移行後 (faster-whisper large-v3 INT8) |
|------|--------------------------|--------------------------------------|
| 日本語WER | ~30-50% | **~8-12%** |
| 推論速度 | 基準 | **4倍高速** |
| VRAM | 1GB | 3-5GB |
| ファイルI/O | 毎回tmpファイル生成 | **NumPy配列直接渡し** |

### 2.3 アーキテクチャ方針

| 提案者 | 推奨 |
|--------|------|
| バックエンドアーキテクト | **モジュラーモノリス → 段階的マイクロサービス化** |
| DevOps | docker-compose によるマルチサービス構成 |
| PM | フェーズごとに複雑さを増やす段階的アプローチ |

**落としどころ: Phase 1はモジュラーモノリス、Phase 2以降でGPUワーカーを分離**

```
Phase 1:
┌──────────────────────────────────┐
│  FastAPI (API + WebSocket + 推論) │
│  PostgreSQL / Redis              │
└──────────────────────────────────┘

Phase 2以降:
┌──────────┐    ┌─────────────────┐
│ FastAPI  │◄──►│ Redis (Queue)   │
│ (API)    │    └────────┬────────┘
└──────────┘             │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         GPU Worker  GPU Worker  GPU Worker
         (Whisper)   (Diarize)   (Emotion)
```

### 2.4 非同期タスクキュー

| 提案者 | 推奨 |
|--------|------|
| バックエンドアーキテクト (1) | **ARQ** (asyncioネイティブ、軽量) |
| バックエンドアーキテクト (2) | **ARQ** or Celery |
| PM | Celery |

**落としどころ: ARQ (Redis)**

- FastAPI + asyncio との親和性が高い
- Celeryは多機能だが個人開発には過剰
- Redis をキャッシュ / Pub/Sub / キューで共用できコスト効率が良い

### 2.5 DB選定

**全員一致: PostgreSQL + Redis**

- PostgreSQL: セッション・発話・話者のリレーション管理、JSONB による柔軟な拡張、pgvector による話者埋め込み検索
- Redis: リアルタイム中間状態、WebSocket通知用Pub/Sub、タスクキュー

### 2.6 インフラ・デプロイ

| 提案者 | 推奨 |
|--------|------|
| DevOps | **セルフホスト (自宅GPU PC + Cloudflare Tunnel)** を第一推奨 |

**落としどころ: セルフホスト優先**

| 構成 | 月額コスト |
|------|-----------|
| **セルフホスト** (自宅GPU PC + Cloudflare Tunnel) | **~3,000円** (電気代のみ) |
| クラウド最安 (Vast.ai スポット) | ~7,500円 |
| クラウド推奨 (GCP L4) | ~55,000円 |

### 2.7 話者分離 (Speaker Diarization)

**全員一致: pyannote-audio 3.1**

- SOTA精度、MITライセンス
- whisperX 経由での統合も選択肢
- リアルタイム用途ではバッファ方式（5-10秒バッチ）が現実的

### 2.8 感情分析

**ML/AIエンジニア提案を採用: ハイブリッド方式**

```
音声信号 → emotion2vec+ → 音声感情スコア ─┐
                                           ├→ 加重平均 (音声0.6 : テキスト0.4) → 最終結果
文字起こしテキスト → 日本語BERT → テキスト感情 ─┘
```

- 音声のみでは日本語の微妙なニュアンスを捉えきれないため、テキストとの併用が重要
- 6感情分類: neutral / happy / sad / angry / surprised / fearful

### 2.9 音声変換 (Voice Conversion)

| 候補 | 用途 | 推奨度 |
|------|------|--------|
| **GPT-SoVITS** | 高品質バッチ変換（3-10秒の参照音声で利用可能） | 第一推奨 |
| **RVC v2** | リアルタイム変換（低遅延） | 第二推奨 |
| CosyVoice 2 | ゼロショット変換 | 将来候補 |

**落としどころ: Phase 4ではオフライン変換から開始し、リアルタイムは将来課題**

---

## 3. 統合ロードマップ（最終版）

### Phase 1: Foundation — MVP（目安 2-3ヶ月）

**ゴール: 「録音して、文字起こしして、保存して、後から見返せる」**

| カテゴリ | タスク | 担当領域 |
|---------|--------|---------|
| **文字起こし** | openai-whisper → faster-whisper 移行 | ML |
| **文字起こし** | Silero VAD 導入（発話区間検出） | ML |
| **文字起こし** | VADベースのセグメンテーション（1秒固定→動的） | ML + Backend |
| **文字起こし** | イベントループブロッキング解消 (`run_in_executor`) | Backend |
| **バックエンド** | PostgreSQL + SQLAlchemy + Alembic 導入 | Backend |
| **バックエンド** | Redis 導入（キャッシュ / セッション管理） | Backend |
| **バックエンド** | セッション / 発話 / タグのCRUD API | Backend |
| **バックエンド** | WebSocketプロトコル正式化 (start/partial/final) | Backend |
| **バックエンド** | JWT認証 | Backend |
| **フロントエンド** | Svelte + Vite + Tailwind CSS 環境構築 | Frontend |
| **フロントエンド** | 録音画面（リアルタイム文字起こし表示） | Frontend |
| **フロントエンド** | ダッシュボード（録音一覧） | Frontend |
| **フロントエンド** | 録音詳細画面（再生 + テキスト同期表示） | Frontend |
| **フロントエンド** | 手動タグ付け・検索UI | Frontend |
| **インフラ** | docker-compose.yml (API + PostgreSQL + Redis) | DevOps |
| **インフラ** | マルチステージ Dockerfile | DevOps |
| **インフラ** | print() → structlog 置換 | DevOps |
| **インフラ** | 既存バグ修正 (UPLOAD_CHUNK_BYTES, .env パス) | Backend |
| **品質** | pytest + httpx テスト基盤 | All |

**完了基準**: 1ユーザーが会議を録音 → リアルタイム文字起こし → 保存 → タグ付け → 後から検索・閲覧できる。

---

### Phase 2: Intelligence — 知能化（目安 2-3ヶ月）

**ゴール: 「誰が何の話をしていたかが自動でわかる」**

| カテゴリ | タスク |
|---------|--------|
| **話者分離** | pyannote-audio 3.1 統合 |
| **話者分離** | Whisperタイムスタンプとの突合（whisperX方式） |
| **話者分離** | 話者埋め込みキャッシュ（セッション内一貫性） |
| **トピック検出** | Embeddingベースのリアルタイムトピック検出 (multilingual-e5-small) |
| **トピック検出** | LLMベースの録音後トピック分析・要約 |
| **自動タグ** | 文字起こし内容からのタグ自動提案 |
| **バックエンド** | ARQワーカー導入（非同期タスク処理） |
| **バックエンド** | Redis Pub/Sub → WebSocket結果プッシュ |
| **フロントエンド** | 話者色分け表示（左ボーダー + ラベル） |
| **フロントエンド** | トピックタイムライン・サイドバー |
| **フロントエンド** | エクスポート (Markdown / SRT) |
| **インフラ** | docker-compose.gpu.yml (GPUオーバーレイ) |
| **インフラ** | GPUワーカー分離 |

**完了基準**: 会議録音を開くと、話者ラベル付き・トピック区切り付きのタイムラインが表示される。

---

### Phase 3: Emotion — 感情分析（目安 2-3ヶ月）

**ゴール: 「声のトーンから感情を読み取り、会話の質を可視化する」**

| カテゴリ | タスク |
|---------|--------|
| **感情分析** | emotion2vec+ 統合（音声ベースSER） |
| **感情分析** | 日本語BERT感情分析（テキストベース） |
| **感情分析** | ハイブリッド融合（音声0.6 + テキスト0.4） |
| **フロントエンド** | 感情カラードット表示（各発話ブロック） |
| **フロントエンド** | 感情タイムライン（話者ごとの感情遷移グラフ） |
| **バックエンド** | 感情データのDB永続化・API |
| **インフラ** | GitHub Actions CI/CD パイプライン |
| **インフラ** | Cloudflare Tunnel + HTTPS |

**完了基準**: 録音の各発話に感情ラベルが付与され、タイムラインで感情の推移が可視化される。

---

### Phase 4: Voice — 音声変換（目安 3-4ヶ月）

**ゴール: 「音声そのものを変換・再創造する」**

| カテゴリ | タスク |
|---------|--------|
| **音声変換** | GPT-SoVITS 統合（オフライン高品質変換） |
| **音声変換** | RVC v2 統合（ニアリアルタイム変換） |
| **音声変換** | キャラクター音声登録（参照音声アップロード） |
| **音声変換** | 感情メタデータ保持変換 |
| **フロントエンド** | キャラクター選択グリッド |
| **フロントエンド** | 変換プレビュー・ダウンロードUI |
| **バックエンド** | MinIO / S3 オブジェクトストレージ |
| **バックエンド** | 変換ジョブ管理API |
| **インフラ** | ModelManager（GPU VRAM動的管理） |

**完了基準**: ユーザーが録音音声を選択し、登録済みキャラクターの声に変換してダウンロードできる。

---

## 4. 技術スタック（最終版）

### 確定スタック

| レイヤー | 技術 | 導入Phase |
|---------|------|-----------|
| **バックエンド** | FastAPI + Uvicorn | 既存 |
| **DB** | PostgreSQL 16 + pgvector | Phase 1 |
| **キャッシュ / キュー** | Redis 7 | Phase 1 |
| **ORM** | SQLAlchemy 2.0 + Alembic | Phase 1 |
| **タスクキュー** | ARQ | Phase 2 |
| **フロントエンド** | Svelte 4 + Vite + Tailwind CSS v4 | Phase 1 |
| **音声認識** | faster-whisper (large-v3 INT8) | Phase 1 |
| **VAD** | Silero VAD (faster-whisper内蔵) | Phase 1 |
| **話者分離** | pyannote-audio 3.1 | Phase 2 |
| **トピック検出** | multilingual-e5-small + BERTopic | Phase 2 |
| **感情分析 (音声)** | emotion2vec+ | Phase 3 |
| **感情分析 (テキスト)** | 日本語BERT (cl-tohoku) | Phase 3 |
| **音声変換** | GPT-SoVITS / RVC v2 | Phase 4 |
| **コンテナ** | Docker + docker-compose | Phase 1 |
| **GPU** | NVIDIA Container Toolkit | Phase 2 |
| **HTTPS** | Cloudflare Tunnel | Phase 3 |
| **CI/CD** | GitHub Actions | Phase 3 |
| **ログ** | structlog (JSON構造化ログ) | Phase 1 |
| **監視** | Dozzle → Prometheus + Grafana | Phase 3-4 |

### GPU要件（段階的）

| Phase | 最低GPU | VRAM | 月額コスト (セルフホスト) |
|-------|---------|------|------------------------|
| Phase 1 | RTX 3060 | 12GB | ~3,000円 (電気代) |
| Phase 2 | RTX 4070 Ti | 16GB | ~3,000円 |
| Phase 3-4 | RTX 4090 or A10 | 24GB | ~3,000-5,000円 |

> **CPU環境でのPhase 1も可能**: faster-whisper medium (INT8 CPU) + Silero VAD で開発を開始し、GPU入手後にlarge-v3へ移行する段階的アプローチも現実的。

---

## 5. データモデル（最終版）

```sql
-- ユーザー
users (id, name, email, created_at)

-- 録音セッション
sessions (id, user_id, title, status, language, duration_sec, audio_path, created_at)

-- 発話セグメント（文字起こしの最小単位）
utterances (id, session_id, speaker_id, seq, start_sec, end_sec, text, confidence, metadata)

-- 話者
speakers (id, session_id, label, color, embedding)

-- 感情分析結果
emotions (id, utterance_id, primary_emotion, scores, arousal, valence)

-- トピック / タグ
topics (id, session_id, name, start_sec, end_sec, confidence, source)

-- 音声変換結果
voice_conversions (id, session_id, character_voice, audio_path, status, created_at)
```

---

## 6. 画面構成（最終版）

### ダッシュボード (`/`)
- 録音開始ボタン（最重要アクション、大きく配置）
- 最近の録音一覧（日時・タグ・時間）
- 簡易統計

### 録音画面 (`/record`)
- リアルタイム文字起こし表示（画面の60%以上）
- 音声波形（フィードバック用）
- 感情インジケーター（Phase 3で追加）
- 停止ボタン（画面下部、誤タップ防止）

### 録音詳細 (`/transcript/:id`)
- 左: トピック目次 + 音声変換パネル
- 右: 話者色分け付き文字起こし本文
- 下部固定: 音声プレーヤー（テキスト同期）

### 設定 (`/settings`)
- マイク選択、言語、認識ウィンドウ
- テーマ、フォントサイズ
- キャラクターボイス設定

---

## 7. リスクと対策（統合版）

| リスク | 影響度 | 対策 |
|--------|--------|------|
| **文字起こし精度が不十分** | 高 | faster-whisper + VAD で大幅改善。kotoba-whisper (日本語特化) をフォールバック |
| **GPU調達** | 中 | Phase 1はCPU (faster-whisper medium) でも開始可能 |
| **スコープクリープ** | 高 | Phase完了基準を厳守。MVPは文字起こし+永続化に集中 |
| **プライバシー・倫理** | 高 | ローカル実行がデフォルト。Voice Conversionには同意フロー必須 |
| **話者分離の日本語精度** | 中 | pyannote + 手動補正UIの併用。精度不足時はユーザーが話者名を修正 |
| **感情分析の信頼性** | 中 | 「参考値」として提示。ユーザー補正機能を提供 |
| **音声変換の品質** | 中 | オフライン変換から開始。リアルタイムは将来課題 |

---

## 8. 直近2週間のアクションアイテム

全エージェントが一致した**最優先事項**:

1. **faster-whisper への移行** — `server/services/whisper.py` を書き換え（~50行、移行コスト低）
2. **Silero VAD 導入** — 1秒固定チャンク → VADベースの動的セグメンテーション
3. **docker-compose.yml 作成** — API + PostgreSQL + Redis のマルチサービス構成
4. **DBスキーマ設計** — sessions / utterances / speakers / topics テーブル作成
5. **既存バグ修正** — `UPLOAD_CHUNK_BYTES` 未定義、`.env` パス誤り、デバッグprint除去

---

## 付録: 各エージェントの個別分析

各エージェントの詳細な分析は以下のファイルに保存されています:

- `docs/perspectives/01-product-manager.md`
- `docs/perspectives/02-backend-architect.md`
- `docs/perspectives/03-ml-ai-engineer.md`
- `docs/perspectives/04-frontend-ux-designer.md`
- `docs/perspectives/05-devops-infra-engineer.md`
