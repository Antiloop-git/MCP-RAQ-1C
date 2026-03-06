"""Тесты для QdrantIndexer — unit-тесты без внешних сервисов."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from indexer import QdrantIndexer


# --- Тесты форматирования (не требуют сервисов) ---

def _make_indexer_no_connect():
    """Создаёт indexer без реального подключения к Qdrant/Embeddings."""
    indexer = QdrantIndexer.__new__(QdrantIndexer)
    indexer.client = None
    indexer.http = None
    return indexer


def test_build_friendly_name():
    indexer = _make_indexer_no_connect()
    obj = {
        "name": "SS_ЗаказКлиента",
        "synonym": "Заказ клиента",
        "object_type_ru": "Документ",
    }
    assert indexer._build_friendly_name(obj) == "Документ: Заказ клиента"


def test_build_friendly_name_no_synonym():
    indexer = _make_indexer_no_connect()
    obj = {"name": "TestObject", "object_type_ru": "Справочник"}
    assert indexer._build_friendly_name(obj) == "Справочник: TestObject"


def test_build_description_basic():
    indexer = _make_indexer_no_connect()
    obj = {
        "name": "SS_ЗаказКлиента",
        "synonym": "Заказ клиента",
        "object_type_ru": "Документ",
        "attributes": [
            {"name": "Фирма", "type_info": ["СправочникСсылка.Организации"]},
            {"name": "Склад", "type_info": []},
        ],
        "tabular_sections": [
            {"name": "Товары", "attributes": [{"name": "Номенклатура"}, {"name": "Количество"}]},
        ],
        "register_records": ["AccumulationRegister.SS_УчетЗаказовКлиентов"],
    }
    desc = indexer._build_description(obj)
    assert "Документ SS_ЗаказКлиента" in desc
    assert "Фирма" in desc
    assert "СправочникСсылка.Организации" in desc
    assert "Товары" in desc
    assert "Номенклатура" in desc
    assert "SS_УчетЗаказовКлиентов" in desc


def test_build_description_enum():
    indexer = _make_indexer_no_connect()
    obj = {
        "name": "ВидыДоставки",
        "synonym": "Виды доставки",
        "object_type_ru": "Перечисление",
        "enum_values": [{"name": "Самовывоз"}, {"name": "Курьер"}, {"name": "Почта"}],
    }
    desc = indexer._build_description(obj)
    assert "Самовывоз" in desc
    assert "Курьер" in desc


def test_build_description_register_with_dimensions():
    indexer = _make_indexer_no_connect()
    obj = {
        "name": "ОстаткиТоваров",
        "synonym": "Остатки товаров",
        "object_type_ru": "РегистрНакопления",
        "dimensions": [{"name": "Номенклатура", "type_info": ["СправочникСсылка.Номенклатура"]}],
        "resources": [{"name": "Количество", "type_info": ["Число"]}],
    }
    desc = indexer._build_description(obj)
    assert "Измерения" in desc
    assert "Номенклатура" in desc
    assert "Ресурсы" in desc
    assert "Количество" in desc


def test_build_payload_structure():
    indexer = _make_indexer_no_connect()
    obj = {
        "name": "SS_ЗаказКлиента",
        "synonym": "Заказ клиента",
        "object_type": "Document",
        "object_type_ru": "Документ",
        "attributes": [{"name": "Фирма", "type_info": []}],
        "tabular_sections": [{"name": "Товары", "attributes": []}],
        "register_records": ["AccumulationRegister.SS_УчетЗаказовКлиентов"],
        "hierarchical": False,
    }
    payload = indexer._build_payload(obj)
    assert payload["object_name"] == "SS_ЗаказКлиента"
    assert payload["object_type"] == "Document"
    assert payload["object_type_ru"] == "Документ"
    assert payload["synonym"] == "Заказ клиента"
    assert payload["friendly_name"] == "Документ: Заказ клиента"
    assert payload["attributes"] == ["Фирма"]
    assert payload["tabular_sections"] == ["Товары"]
    assert payload["register_records"] == ["AccumulationRegister.SS_УчетЗаказовКлиентов"]
    assert "description" in payload
    assert len(payload["description"]) > 0


def test_build_description_truncates_enum_values():
    indexer = _make_indexer_no_connect()
    obj = {
        "name": "БольшоеПеречисление",
        "synonym": "Большое",
        "object_type_ru": "Перечисление",
        "enum_values": [{"name": f"Значение{i}"} for i in range(25)],
    }
    desc = indexer._build_description(obj)
    assert "Значение0" in desc
    assert "Значение19" in desc
    assert "ещё 5" in desc
