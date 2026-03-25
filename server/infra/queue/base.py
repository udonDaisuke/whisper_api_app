"""JobQueue インタフェース定義。

Stage 2 で ARQQueue に差し替えるための受け皿となる ABC。
"""
from abc import ABC, abstractmethod
from typing import Any


class JobQueue(ABC):
    """ジョブキューの抽象基底クラス。

    Stage 1: SynchronousQueue（メモリ内同期実行）
    Stage 2: ARQQueue（Redis バックエンドの非同期キュー）
    """

    @abstractmethod
    def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any],
        priority: int = 0,
    ) -> str:
        """ジョブをキューに追加する。

        Args:
            job_type: ジョブの種別識別子。
            payload: ジョブ実行に必要なデータ。
            priority: 優先度（数値が大きいほど高優先）。

        Returns:
            発行されたジョブ ID。
        """
        ...

    @abstractmethod
    def dequeue(self) -> dict[str, Any] | None:
        """キューから次のジョブを取り出す。

        Returns:
            ジョブデータ（job_id, job_type, payload を含む辞書）。
            キューが空の場合は None。
        """
        ...

    @abstractmethod
    def ack(self, job_id: str) -> None:
        """ジョブの正常完了を通知する。

        Args:
            job_id: 完了したジョブの ID。
        """
        ...

    @abstractmethod
    def nack(self, job_id: str, reason: str) -> None:
        """ジョブの失敗を通知する。

        Args:
            job_id: 失敗したジョブの ID。
            reason: 失敗理由の説明。
        """
        ...
