"""GPUComputeAdapter スタブ。

Stage 3 (CUDA / float16) 向け GPU 推論アダプター。
現時点では NotImplementedError を返すスタブとして定義する。
COMPUTE_DEVICE=cuda に設定されると起動時に警告を出す。
"""
from __future__ import annotations

import logging
from typing import Any

from server.compute.base import ComputeAdapter
from server.core.config import settings

logger = logging.getLogger(__name__)


class GPUComputeAdapter(ComputeAdapter):
    """CUDA / float16 を使用した GPU 推論アダプター (Stage 3 実装予定)。

    RULE-S3 準拠: COMPUTE_DEVICE=cuda への切り替えのみで GPU 推論に移行できる。
    現バージョンはスタブ。Stage 3 実装時に本体を追加する。
    """

    def __init__(self) -> None:
        logger.warning(
            "GPUComputeAdapter is a stub and not yet implemented. "
            "Set COMPUTE_DEVICE=cpu to use the CPU adapter."
        )

    @property
    def device(self) -> str:
        return "cuda"

    @property
    def compute_type(self) -> str:
        return settings.COMPUTE_TYPE

    def infer(self, model_handle: Any, input_data: Any) -> Any:
        raise NotImplementedError(
            "GPUComputeAdapter is not implemented in Stage 1/2. "
            "Use COMPUTE_DEVICE=cpu or implement Stage 3 GPU support."
        )
