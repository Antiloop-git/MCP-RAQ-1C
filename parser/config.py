"""Конфигурация парсера."""

import os
from pathlib import Path

CONFIG_PATH = Path(os.getenv("CONFIG_PATH", "./configuration/Prod"))
HBK_PATH = Path(os.getenv("HBK_PATH", "./bin/1cv8_ru.hbk"))
HOST = os.getenv("PARSER_HOST", "0.0.0.0")
PORT = int(os.getenv("PARSER_PORT", "8001"))
