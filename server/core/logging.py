"""
構造化ロギング設定モジュール。

JSON 形式でログを出力する。アプリケーション起動時に setup_logging() を呼び出すこと。
"""
import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """ログレコードを JSON 形式にフォーマットするハンドラ。"""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: int = logging.DEBUG) -> None:
    """アプリケーション全体のロギングを設定する。

    Args:
        level: ルートロガーのログレベル。デフォルトは DEBUG。
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    # 既存ハンドラを除去して重複出力を防ぐ
    root.handlers.clear()
    root.addHandler(handler)
