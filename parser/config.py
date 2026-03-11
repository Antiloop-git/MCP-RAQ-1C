"""Конфигурация парсера."""

import os
from pathlib import Path

CONFIG_PATH = Path(os.getenv("CONFIG_PATH", "./configuration/Prod"))
HOST = os.getenv("PARSER_HOST", "0.0.0.0")
PORT = int(os.getenv("PARSER_PORT", "8001"))
