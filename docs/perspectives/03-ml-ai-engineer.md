# ML/AIエンジニア視点の分析

## 1. 文字起こし精度向上

### モデル選定: faster-whisper large-v3 (INT8) を強く推奨

| モデル | 日本語CER目安 | VRAM (FP16) | RTF (GPU) |
|--------|-------------|------------|-----------|
| openai-whisper tiny (現状) | ~40-50% | 1GB | 0.3 (CPU) |
| **faster-whisper large-v3 (INT8)** | **~8-12%** | **3GB** | **0.05** |
| Kotoba-Whisper v2.2 (日本語特化) | ~7-10% | 3GB | 0.05 |

### VAD (Silero VAD) 導入

- faster-whisper の `vad_filter=True` で内蔵利用可能
- 無音区間スキップにより推論速度30-50%向上
- ハルシネーション大幅削減

### ウィンドウ戦略改善

1秒固定 → VADベース動的セグメンテーション（発話単位、最大30秒）

## 2. 話者分離

### 推奨: pyannote-audio 3.1

- SOTA精度 (DER ~10-15%)
- whisperX 経由の統合が最も簡潔
- リアルタイムは5-10秒バッファのバッチ処理

### 統合方式 (whisperX)

```
音声 → faster-whisper (文字起こし + word timestamps)
    → whisperX.align() (単語レベルアライメント)
    → pyannote diarization (話者区間検出)
    → whisperX.assign_word_speakers() (話者ラベル付与)
```

## 3. 感情分析

### ハイブリッド方式を推奨

```
音声信号 → emotion2vec+ → 音声感情スコア (9次元) ─┐
                                                    ├→ 加重平均 → 最終結果
文字起こし → 日本語BERT → テキスト感情スコア ────────┘
```

- 音声0.6 : テキスト0.4 の加重平均
- 日本語は感情表出が抑制的なため、テキスト側も重要
- 6分類: neutral / happy / sad / angry / surprised / fearful

## 4. トピック検出

### 二段構成

- **リアルタイム**: Embeddingベース (multilingual-e5-small) で事前定義トピックとの類似度
- **録音後バッチ**: ローカルLLM (Qwen2.5-7B) による詳細なトピックセグメンテーション・要約

## 5. 音声変換

### 推奨構成

- **GPT-SoVITS**: 高品質バッチ変換（3-10秒のリファレンスで利用可能）
- **RVC v2**: リアルタイム変換（低遅延、RTF ~0.05）

Phase 4ではオフライン変換から開始。

## 6. GPU要件

| 構成 | GPU | 対応機能 |
|------|-----|---------|
| ミニマム | RTX 3060 12GB | 文字起こし + VAD + トピック |
| 推奨 | RTX 4070 Ti 16GB | 全機能 (VC除くリアルタイム) |
| フル | RTX 4090 24GB | 全機能リアルタイム同時実行 |

### CPU環境での段階的導入

- Phase 1: CPU → faster-whisper medium (INT8 CPU) + Silero VAD
- Phase 2: GPU 12-16GB → large-v3 + pyannote + emotion2vec
- Phase 3: GPU 24GB+ → + RVC + LLM

## 7. 最優先: P0

faster-whisper + VAD 導入だけで、現状 tiny 比で **文字起こし精度を3-5倍改善**でき、推論速度も向上する。
