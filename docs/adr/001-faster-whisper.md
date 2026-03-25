# ADR-001: OpenAI Whisper → Faster Whisper (CTranslate2) 移行

> ステータス: Accepted
> 日付: 2026-03-26
> 決定者: udonDaisuke

## 背景

現状は `openai-whisper` + `torch` で動作しているが、16GB RAM の CPU 環境でリアルタイム文字起こしを実現するにはパフォーマンスが不足している。

## 決定

`openai-whisper` と `torch` を除去し、`faster-whisper` (CTranslate2 ベース) に移行する。

## 理由

| 指標 | openai-whisper | faster-whisper | 差分 |
|------|----------------|----------------|------|
| CPU 推論速度 (1秒音声) | ~2秒 (small) | ~0.5秒 (small, int8) | **4倍高速** |
| メモリ使用量 (small) | ~2GB (torch フル) | ~1GB (CTranslate2) | **50%削減** |
| Docker イメージサイズ | 大 (torch 含む) | 小 (torch 不要) | 大幅削減 |

`int8` 量子化により 16GB RAM 自宅端末で small モデルがリアルタイム動作可能になる。

## 影響範囲

- `server/services/whisper.py` → `server/plugins/transcribe/faster_whisper.py` に書き直し
- `requirements.txt` から `openai-whisper`, `torch` を除去し `faster-whisper` を追加
- Dockerfile から `ffmpeg` は引き続き必要

## 撤回条件

- `faster-whisper` のライセンスまたは API が破壊的変更を受けた場合
- より優れた CPU 対応モデル (Whisper.cpp 等) に移行する場合
