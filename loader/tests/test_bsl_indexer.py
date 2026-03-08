"""Тесты для BslIndexer — функция _parse_bsl_file."""

import sys
import os
from pathlib import Path
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from indexer import _parse_bsl_file, BslIndexer, BslChunk


def _write_bsl(content: str, filename: str = "SS_ТестДок.ObjectModule.bsl",
               object_type: str = "Document") -> tuple[Path, Path]:
    """Создаёт временный .bsl файл в структуре .../base/{ObjectType}/{filename}.

    Реальная структура: modules/{ObjectType}/{ObjectName}.{ModuleType}.bsl
    """
    tmp = tempfile.mkdtemp()
    base = Path(tmp)
    type_dir = base / object_type
    type_dir.mkdir()
    bsl = type_dir / filename
    bsl.write_text(content, encoding="utf-8")
    return bsl, base


# ---- Парсинг имени файла / object_type из папки ----

def test_parse_filename_empty_file():
    """Пустой файл → ноль чанков."""
    path, base = _write_bsl("")
    chunks = _parse_bsl_file(path, base)
    assert chunks == []


def test_parse_filename_parts():
    """Правильное извлечение object_type из папки, object_name и module_type из имени файла."""
    path, base = _write_bsl(
        "Процедура Тест()\nКонецПроцедуры",
        filename="SS_РасходнаяНакладная.ObjectModule.bsl",
        object_type="Document",
    )
    chunks = _parse_bsl_file(path, base)
    assert len(chunks) == 1
    assert chunks[0].object_type == "Document"
    assert chunks[0].object_name == "SS_РасходнаяНакладная"
    assert chunks[0].module_type == "ObjectModule"


# ---- Чанкинг: файл без процедур ----

def test_no_procs_single_chunk():
    path, base = _write_bsl("// Просто комментарий\nПеременная А = 1;")
    chunks = _parse_bsl_file(path, base)
    assert len(chunks) == 1
    assert chunks[0].proc_name == "<module>"
    assert "Переменная А" in chunks[0].chunk_text


# ---- Чанкинг: несколько процедур ----

def test_multiple_procs():
    code = """\
// Инициализация
Перем А;

Процедура ПервыйМетод()
    А = 1;
КонецПроцедуры

Функция ВторойМетод()
    Возврат А;
КонецФункции
"""
    path, base = _write_bsl(code)
    chunks = _parse_bsl_file(path, base)
    # Ожидаем: преамбула + 2 процедуры
    assert len(chunks) == 3
    assert chunks[0].proc_name == "<module>"
    proc_names = {c.proc_name for c in chunks}
    assert "ПервыйМетод()" in proc_names
    assert "ВторойМетод()" in proc_names


# ---- Чанкинг: английские ключевые слова (EDT) ----

def test_english_keywords():
    code = """\
Procedure DoSomething()
    // code
EndProcedure

Function GetResult()
    Return 1;
EndFunction
"""
    path, base = _write_bsl(code)
    chunks = _parse_bsl_file(path, base)
    assert len(chunks) == 2
    proc_names = {c.proc_name for c in chunks}
    assert "DoSomething()" in proc_names
    assert "GetResult()" in proc_names


# ---- Чанкинг: обрезка до 4000 символов ----

def test_chunk_truncated_to_4000():
    long_body = "А" * 5000
    code = f"Процедура Большая()\n{long_body}\nКонецПроцедуры"
    path, base = _write_bsl(code)
    chunks = _parse_bsl_file(path, base)
    assert len(chunks) == 1
    assert len(chunks[0].chunk_text) <= 4000


# ---- BslIndexer: структура (без реальных сервисов) ----

def test_bsl_indexer_no_connect():
    indexer = BslIndexer.__new__(BslIndexer)
    indexer.client = None
    indexer.http = None
    assert indexer.CODE_VECTOR_NAME == "code"
