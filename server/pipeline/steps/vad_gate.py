"""VAD ゲートステップ。

無音区間 (RMS がしきい値以下) の PCM チャンクを TranscriptionStep に渡さずスキップする。
CPU 推論コストの削減とリアルタイム遅延改善が目的。
"""
from __future__ import annotations

import logging
import math
import struct
from typing import Any

from server.core.config import settings
from server.pipeline.steps.base import PipelineContext, PipelineStep

logger = logging.getLogger(__name__)


class VADGate(PipelineStep):
    """Voice Activity Detection ゲートステップ。

    RMS (Root Mean Square) を用いた簡易エネルギーベース VAD。
    しきい値は settings.VAD_SILENCE_THRESHOLD で外部化する (RULE-Q3)。
    """

    def process(self, context: PipelineContext, input: bytes) -> bytes | None:
        """PCM チャンクの音声活動を検出し、無音なら None を返す。

        Args:
            context: パイプライン実行コンテキスト。
            input: PCM 16-bit little-endian のバイト列。

        Returns:
            音声あり: 元の input をそのまま返す。
            無音: None (Orchestrator がスキップ)。
        """
        rms = self._compute_rms(input)
        if rms <= settings.VAD_SILENCE_THRESHOLD:
            logger.debug(
                "vad_gate: silence detected, skipping chunk",
                extra={"session_id": context.session_id, "rms": round(rms, 2)},
            )
            return None
        return input

    @staticmethod
    def _compute_rms(pcm_bytes: bytes) -> float:
        """PCM 16-bit little-endian バイト列の RMS を計算する。

        Args:
            pcm_bytes: 16-bit LE 符号付き整数のバイト列。

        Returns:
            RMS 値 (0.0 以上)。空バイト列の場合は 0.0。
        """
        if not pcm_bytes:
            return 0.0
        n = len(pcm_bytes) // 2
        if n == 0:
            return 0.0
        samples = struct.unpack_from(f"<{n}h", pcm_bytes)
        mean_sq = sum(s * s for s in samples) / n
        return math.sqrt(mean_sq)
