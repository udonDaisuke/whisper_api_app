"""ComputeAdapter ファクトリ。

環境変数 COMPUTE_DEVICE に基づいて適切なアダプターを返す。
RULE-S2: Stage 切り替えはコード変更なく環境変数のみで行う。
"""
from __future__ import annotations

import logging

from server.compute.base import ComputeAdapter
from server.core.config import settings

logger = logging.getLogger(__name__)


def get_compute_adapter() -> ComputeAdapter:
    """COMPUTE_DEVICE 設定に基づいて ComputeAdapter を返す。

    Returns:
        CPUComputeAdapter (COMPUTE_DEVICE=cpu) または
        GPUComputeAdapter (COMPUTE_DEVICE=cuda)。

    Raises:
        ValueError: 未知の COMPUTE_DEVICE が設定された場合。
    """
    device = settings.COMPUTE_DEVICE.lower()

    if device == "cpu":
        from server.compute.cpu import CPUComputeAdapter
        adapter = CPUComputeAdapter()
        logger.info(
            "ComputeAdapter initialized",
            extra={"device": adapter.device, "compute_type": adapter.compute_type},
        )
        return adapter

    if device == "cuda":
        from server.compute.gpu import GPUComputeAdapter
        adapter = GPUComputeAdapter()
        logger.info(
            "ComputeAdapter initialized",
            extra={"device": adapter.device, "compute_type": adapter.compute_type},
        )
        return adapter

    raise ValueError(
        f"Unknown COMPUTE_DEVICE: {settings.COMPUTE_DEVICE!r}. "
        "Valid values: cpu, cuda"
    )
