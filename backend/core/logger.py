"""Centralized logging configuration for GSTAgent.

Provides structured logging with context information (user_id, firm_id, etc)
to help with debugging and monitoring.
"""

import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime
from core.config import LOG_LEVEL, LOG_FILE


class StructuredFormatter(logging.Formatter):
    """Formats log records as JSON for better parsing and analysis."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields if provided
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data, default=str)


class ContextualLogger:
    """Logger wrapper that includes request context (user_id, firm_id, etc)."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}

    def set_context(self, **kwargs) -> None:
        """Set request context."""
        self.context.update(kwargs)

    def clear_context(self) -> None:
        """Clear request context."""
        self.context.clear()

    def _log(
        self,
        level: int,
        message: str,
        *args,
        extra_data: Optional[Dict] = None,
        exc_info: bool = False,
        **kwargs
    ) -> None:
        """Internal logging method."""
        record = logging.LogRecord(
            name=self.logger.name,
            level=level,
            pathname="",
            lineno=0,
            msg=message,
            args=args,
            exc_info=exc_info,
        )

        # Add context and extra data
        extra = {"extra_data": {**self.context, **(extra_data or {})}}
        record.extra_data = extra["extra_data"]

        self.logger.handle(record)

    def debug(
        self,
        message: str,
        *args,
        extra_data: Optional[Dict] = None,
        **kwargs
    ) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, *args, extra_data=extra_data, **kwargs)

    def info(
        self,
        message: str,
        *args,
        extra_data: Optional[Dict] = None,
        **kwargs
    ) -> None:
        """Log info message."""
        self._log(logging.INFO, message, *args, extra_data=extra_data, **kwargs)

    def warning(
        self,
        message: str,
        *args,
        extra_data: Optional[Dict] = None,
        **kwargs
    ) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, *args, extra_data=extra_data, **kwargs)

    def error(
        self,
        message: str,
        *args,
        extra_data: Optional[Dict] = None,
        exc_info: bool = False,
        **kwargs
    ) -> None:
        """Log error message."""
        self._log(
            logging.ERROR,
            message,
            *args,
            extra_data=extra_data,
            exc_info=exc_info,
            **kwargs
        )

    def critical(
        self,
        message: str,
        *args,
        extra_data: Optional[Dict] = None,
        exc_info: bool = False,
        **kwargs
    ) -> None:
        """Log critical message."""
        self._log(
            logging.CRITICAL,
            message,
            *args,
            extra_data=extra_data,
            exc_info=exc_info,
            **kwargs
        )


def setup_logging() -> None:
    """Configure logging for the application."""
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_formatter = StructuredFormatter()
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (if configured)
    if LOG_FILE:
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setLevel(LOG_LEVEL)
        file_handler.setFormatter(console_formatter)
        root_logger.addHandler(file_handler)

    # SQLAlchemy query logging (controlled by SQL_ECHO in config)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)


def get_logger(name: str) -> ContextualLogger:
    """Get a logger instance with context support.

    Usage:
        logger = get_logger(__name__)
        logger.set_context(user_id="123", firm_id="456")
        logger.info("User action performed")
        # Logs will include user_id and firm_id
    """
    return ContextualLogger(name)


# Initialize logging on module import
setup_logging()


# Common logger instances
logger = get_logger("gstagent")
auth_logger = get_logger("gstagent.auth")
db_logger = get_logger("gstagent.database")
gsp_logger = get_logger("gstagent.gsp")
reconciliation_logger = get_logger("gstagent.reconciliation")
integration_logger = get_logger("gstagent.integration")
