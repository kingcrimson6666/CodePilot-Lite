from __future__ import annotations

import logging

import structlog


class LoggerFactory:
    @staticmethod
    def configure(level: str = "INFO") -> None:
        resolved_level = getattr(logging, level.upper(), logging.INFO)
        logging.basicConfig(level=resolved_level)
        for noisy_logger in (
            "httpx",
            "httpcore",
            "openai",
            "chromadb",
            "urllib3",
        ):
            logging.getLogger(noisy_logger).setLevel(logging.WARNING)
        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    @staticmethod
    def get_logger(name: str = "codepilot"):
        return structlog.get_logger(name)
