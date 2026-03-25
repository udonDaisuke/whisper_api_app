"""PipelineStep インタフェース定義。

ISSUE #13 で PipelineOrchestrator と共に拡張される基盤 ABC。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineContext:
    """パイプライン実行コンテキスト。

    各ステップ間で共有され、副作用イベントの積み上げに使用する (RULE-L3)。
    """

    session_id: str
    events: list[dict[str, Any]] = field(default_factory=list)


class PipelineStep(ABC):
    """RT / バッチパイプラインの処理ステップ抽象基底クラス。

    実装上の制約 (RULE-L3):
    - process() は純粋な変換のみ行う。
    - DB 書き込み・外部 HTTP・ファイル IO を直接実行しない。
    - 副作用が必要な場合は context.events にイベントを積む。

    戻り値として None を返した場合、Orchestrator はこのチャンクをスキップする。
    """

    @abstractmethod
    def process(self, context: PipelineContext, input: Any) -> Any:
        """入力を処理して結果を返す。

        Args:
            context: 実行コンテキスト (session_id, events)。
            input: 前ステップからの出力データ。

        Returns:
            次ステップへ渡すデータ。None の場合はチャンクをスキップ。
        """
        ...
