"""ComputeAdapter インタフェース定義。

CPU / GPU など推論バックエンドの共通インタフェースを定義する。
Plugin 層はこのインタフェースのみに依存し、デバイス固有の実装を知らない。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ComputeAdapter(ABC):
    """推論バックエンドの共通インタフェース。

    RULE-S3: GPUAdapter への切り替えは環境変数 COMPUTE_DEVICE=cuda のみで完結する。
    Plugin 層は ComputeAdapter.infer() を呼ぶだけでよく、デバイス固有コードを持たない。
    """

    @property
    @abstractmethod
    def device(self) -> str:
        """推論デバイス識別子 (例: "cpu", "cuda")。"""

    @property
    @abstractmethod
    def compute_type(self) -> str:
        """量子化・精度設定 (例: "int8", "float16")。"""

    @abstractmethod
    def infer(self, model_handle: Any, input_data: Any) -> Any:
        """推論を実行する。

        Args:
            model_handle: ロード済みモデルオブジェクト。
            input_data: 推論入力データ（音声ファイルパスなど）。

        Returns:
            推論結果。形式はモデル依存。
        """
