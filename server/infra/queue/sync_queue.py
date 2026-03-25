"""SynchronousQueue: メモリ内同期実行キュー（Stage 1 実装）。

Stage 2 で ARQQueue に差し替えるまでの暫定実装。
enqueue 時にジョブを即時実行するのではなく、FIFO キューに積む。
"""
import logging
import uuid
from collections import deque
from typing import Any

from server.infra.queue.base import JobQueue

logger = logging.getLogger(__name__)


class SynchronousQueue(JobQueue):
    """メモリ内 FIFO キュー。

    スレッドセーフではない。Stage 1 のシングルプロセス環境向け。
    Stage 2 移行時は ARQQueue に差し替える（インタフェース互換）。
    """

    def __init__(self) -> None:
        self._queue: deque[dict[str, Any]] = deque()
        self._in_flight: dict[str, dict[str, Any]] = {}

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
            priority: 優先度（SynchronousQueue では未使用、ARQ 移行時に有効化）。

        Returns:
            発行されたジョブ ID（UUID4）。
        """
        job_id = str(uuid.uuid4())
        job = {"job_id": job_id, "job_type": job_type, "payload": payload}
        self._queue.append(job)
        logger.debug("enqueued job_id=%s job_type=%s", job_id, job_type)
        return job_id

    def dequeue(self) -> dict[str, Any] | None:
        """キューから次のジョブを取り出す。

        Returns:
            ジョブデータ（job_id, job_type, payload を含む辞書）。
            キューが空の場合は None。
        """
        if not self._queue:
            return None
        job = self._queue.popleft()
        self._in_flight[job["job_id"]] = job
        logger.debug("dequeued job_id=%s", job["job_id"])
        return job

    def ack(self, job_id: str) -> None:
        """ジョブの正常完了を通知する。

        Args:
            job_id: 完了したジョブの ID。
        """
        self._in_flight.pop(job_id, None)
        logger.debug("ack job_id=%s", job_id)

    def nack(self, job_id: str, reason: str) -> None:
        """ジョブの失敗を通知する。

        Args:
            job_id: 失敗したジョブの ID。
            reason: 失敗理由の説明。
        """
        job = self._in_flight.pop(job_id, None)
        if job is not None:
            logger.warning("nack job_id=%s reason=%s", job_id, reason)
        else:
            logger.warning("nack called for unknown job_id=%s reason=%s", job_id, reason)
