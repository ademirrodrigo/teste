"""Funções auxiliares compartilhadas."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from ..config import settings


def setup_logging() -> logging.Logger:
    """Configura um logger com saída em arquivo e console."""
    logs_dir = settings.log_dir
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("coletor_fiscal")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(logs_dir / "coletor.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


def ensure_subdirectories(base: Path, subfolders: Iterable[str]) -> None:
    """Garante que subdiretórios existam dentro de uma pasta base."""
    for folder in subfolders:
        (base / folder).mkdir(parents=True, exist_ok=True)
