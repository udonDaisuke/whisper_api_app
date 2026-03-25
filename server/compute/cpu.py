"""CPUComputeAdapter 実装。

CTranslate2 バックエンドによる CPU 推論アダプター。
COMPUTE_DEVICE=cpu かつ COMPUTE_TYPE=int8 が標準設定。
"""
from __future__ import annotations

import logging
from typing import Any

from server.compute.base import ComputeAdapter
from server.core.config import settings

logger = logging.getLogger(__name__)


class CPUComputeAdapter(ComputeAdapter):
    """CTranslate2 (int8) を使用した CPU 推論アダプター。

    Stage 1 / Stage 2 の標準バックエンド。
    RULE-S3: Stage 3 への移行は COMPUTE_DEVICE=cuda への切り替えのみで完結する。
    """

    @property
    def device(self) -> str:
        return "cpu"

    @property
    def compute_type(self) -> str:
        return settings.COMPUTE_TYPE

    def infer(self, model_handle: Any, input_data: Any) -> Any:
        """CTranslate2 モデルを使用して推論を実行する。

        Args:
            model_handle: FasterWhisper 等の CTranslate2 ベースのモデルオブジェクト。
            input_data: 音声ファイルパス (str または Path)。

        Returns:
            推論結果 (segments, info のタプル)。
        """
        logger.debug(
            "CPUComputeAdapter.infer called",
            extra={"compute_type": self.compute_type, "input": str(input_data)},
        )
        segments, info = model_handle.transcribe(
            str(input_data),
            beam_size=5,
            condition_on_previous_text=False,
            temperature=0.0,
            no_speech_threshold=0.4,
        )
        return segments, info
