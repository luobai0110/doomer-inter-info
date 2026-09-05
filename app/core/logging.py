import logging
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from structlog.typing import EventDict, Processor

from app.core.config import settings

JSON_FIELD_ORDER = ("timestamp", "level", "logger", "event")
LOG_TIMEZONE = ZoneInfo("Asia/Shanghai")


def _resolve_log_level() -> int:
    """解析配置中的日志级别。"""
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        raise ValueError(f"无效的日志级别: {settings.log_level}")
    return level


def _make_file_handler(formatter: structlog.stdlib.ProcessorFormatter) -> logging.Handler:
    """创建容器内的持久化 JSON 日志文件 handler。"""
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = TimedRotatingFileHandler(
        filename=log_dir / "inter.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(formatter)
    return handler


def _canonical_field_order(
    _logger: Any,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """统一 JSON 字段顺序：公共字段在前，业务字段在后。"""
    ordered = {key: event_dict[key] for key in JSON_FIELD_ORDER if key in event_dict}
    ordered.update(
        {key: value for key, value in event_dict.items() if key not in JSON_FIELD_ORDER}
    )
    return ordered


def _drop_color_message(
    _logger: Any,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """丢弃 Uvicorn 附带的 color_message，避免 ANSI 转义进入 JSON。"""
    event_dict.pop("color_message", None)
    return event_dict


def _add_local_timestamp(
    _logger: Any,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """按上海时间生成 yyyy-MM-dd HH:mm:ss.SSS 格式时间戳。"""
    now = datetime.now(LOG_TIMEZONE)
    event_dict["timestamp"] = (
        f"{now.strftime('%Y-%m-%d %H:%M:%S')}.{now.microsecond // 1000:03d}"
    )
    return event_dict


def _make_formatter(
    shared_processors: list[Processor],
) -> structlog.stdlib.ProcessorFormatter:
    """构造所有日志 handler 共用的 JSON formatter。"""
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            _canonical_field_order,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取项目统一的结构化日志记录器。"""
    return structlog.get_logger(name)


def configure_logging() -> None:
    """将应用和 Uvicorn 日志统一输出为单行 JSON。"""
    level = _resolve_log_level()
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        _drop_color_message,
        _add_local_timestamp,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = _make_formatter(shared_processors)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    file_handler = _make_file_handler(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(level)

    # Uvicorn 默认有独立 handler；接管后所有运行时日志也走同一个 JSON 渲染器。
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
