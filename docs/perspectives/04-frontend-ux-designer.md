# フロントエンド/UXデザイナー視点の分析

## 1. フレームワーク選定: Svelte + Vite

### 理由

1. **既存資産との親和性** — RecorderクラスとAudioWorkletはそのまま流用可能
2. **リアルタイムUI更新** — 変数代入だけでDOM更新、Reactの再レンダリングコスト不要
3. **バンドルサイズ** — ランタイムほぼゼロ、モバイル環境に最適
4. **学習コスト** — Vanilla JSからの移行が最も自然

### ビルド構成

```
client/
├── vite.config.js
├── public/audio/recorder.worklet.js  (AudioWorkletはpublicに配置)
└── src/
    ├── App.svelte
    ├── lib/
    │   ├── audio/recorder.js          (既存Recorderクラス流用)
    │   ├── ws/websocket.js            (WebSocketサービス)
    │   └── stores/                    (Svelte stores)
    ├── components/
    │   ├── recording/                 (録音UI)
    │   ├── transcription/             (文字起こし表示)
    │   ├── speakers/                  (話者表示)
    │   ├── emotion/                   (感情可視化)
    │   └── voice-convert/             (音声変換UI)
    └── routes/                        (SPA内ルーティング)
```

## 2. 画面構成

### ダッシュボード (`/`)
- RECボタン（最重要アクション、大きく配置）
- 最近の録音一覧
- 簡易統計

### 録音画面 (`/record`)
- リアルタイム文字起こし（画面の60%以上）
- 音声波形（フィードバック用）
- 感情インジケーター（Phase 3）
- 停止ボタン（画面下部、誤タップ防止）

### 録音詳細 (`/transcript/:id`)
- 左サイドバー: トピック目次 + 音声変換パネル
- 右メイン: 話者色分け付き文字起こし本文
- 下部固定: 音声プレーヤー（テキスト同期）

### 設定 (`/settings`)
- マイク選択、言語、認識パラメータ
- テーマ、フォントサイズ
- キャラクターボイス設定

## 3. リアルタイム文字起こしUX

### テキスト表示の3層モデル

1. **確定テキスト** (final済み) — 通常テキスト
2. **暫定テキスト** (partial) — opacity: 0.7
3. **認識中インジケーター** — 脈動アニメーション

### スクロール戦略

- 自動スクロール ON (デフォルト): 最新テキストが常に可視
- ユーザーが上にスクロール → 自動OFF + 「最新へ↓」フローティングボタン

## 4. 話者・感情の可視化

### 話者カラーパレット（色覚多様性に配慮）

```css
--speaker-1: #4A90D9;  /* 青 */
--speaker-2: #E8854A;  /* オレンジ */
--speaker-3: #50B86C;  /* 緑 */
--speaker-4: #D94A6B;  /* ローズ */
--speaker-5: #9B6CD9;  /* 紫 */
```

- 左ボーダー (4px solid) + 話者名テキストで二重エンコーディング
- 色だけに依存しない（アクセシビリティ）

### 感情表示

- Level 1: テキストラベル
- Level 2: カラードット + ラベル（推奨）
- Level 3: 感情タイムライン（SVG/Chart.js）

## 5. レスポンシブ対応

| 画面 | モバイル | デスクトップ |
|------|---------|------------|
| 録音画面 | 文字起こし全画面、波形は折りたたみ | フル表示 |
| 結果画面 | トピックはタブ切替、変換はボトムシート | 2カラム |

- `navigator.wakeLock` で録音中の画面ロック防止
- 最小タップサイズ 44px x 44px

## 6. 技術選定

| カテゴリ | 選定 |
|---------|------|
| UIフレームワーク | Svelte 4 + Vite |
| CSS | Tailwind CSS v4 |
| 状態管理 | Svelte stores (writable/derived) |
| ルーティング | svelte-spa-router |
| アイコン | Lucide Icons |
| 波形 | wavesurfer.js |
| テスト | Vitest + @testing-library/svelte |

## 7. アクセシビリティ

- セマンティックHTML (`<main>`, `<article>`, `<nav>`)
- `aria-live="polite"` で文字起こし領域のスクリーンリーダー対応
- WCAG AA準拠のコントラスト比
- `prefers-reduced-motion` 対応
- `<html lang="ja">`
