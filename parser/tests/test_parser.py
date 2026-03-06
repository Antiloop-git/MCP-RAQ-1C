"""Тесты для парсера XML-метаданных 1С."""

import sys
from pathlib import Path

import pytest

# Добавляем parser/ в sys.path для импорта модулей
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import ObjectType
from type_resolver import format_type_with_qualifiers, resolve_type
from xml_parser import parse_directory, parse_file

FIXTURES = Path(__file__).resolve().parent / "fixtures"


# === type_resolver ===


class TestResolveType:
    def test_primitive_string(self):
        assert resolve_type("xs:string") == "Строка"

    def test_primitive_decimal(self):
        assert resolve_type("xs:decimal") == "Число"

    def test_primitive_boolean(self):
        assert resolve_type("xs:boolean") == "Булево"

    def test_primitive_datetime(self):
        assert resolve_type("xs:dateTime") == "Дата"

    def test_catalog_ref(self):
        assert resolve_type("cfg:CatalogRef.Номенклатура") == "СправочникСсылка.Номенклатура"

    def test_document_ref(self):
        assert resolve_type("cfg:DocumentRef.РеализацияТоваров") == "ДокументСсылка.РеализацияТоваров"

    def test_enum_ref(self):
        assert resolve_type("cfg:EnumRef.ВидыОплат") == "ПеречислениеСсылка.ВидыОплат"

    def test_unknown_type_passthrough(self):
        assert resolve_type("cfg:SomethingUnknown.Test") == "cfg:SomethingUnknown.Test"


class TestFormatTypeWithQualifiers:
    def test_string_with_length(self):
        result = format_type_with_qualifiers(["Строка"], string_length=25)
        assert "Строка" in result
        assert "25" in result

    def test_number_with_precision(self):
        result = format_type_with_qualifiers(["Число"], number_digits=15, number_fraction=2)
        assert "Число" in result
        assert "15" in result
        assert "2" in result

    def test_single_ref_type(self):
        result = format_type_with_qualifiers(["СправочникСсылка.Номенклатура"])
        assert result == "СправочникСсылка.Номенклатура"


# === parse_file: Catalog ===


class TestParseCatalog:
    @pytest.fixture()
    def catalog(self):
        return parse_file(FIXTURES / "Catalogs" / "TestCatalog.xml")

    def test_basic_fields(self, catalog):
        assert catalog is not None
        assert catalog.name == "Номенклатура"
        assert catalog.synonym == "Номенклатура"
        assert catalog.comment == "Справочник товаров"
        assert catalog.object_type == ObjectType.CATALOG

    def test_catalog_specific(self, catalog):
        assert catalog.hierarchical is True
        assert catalog.code_length == 11
        assert catalog.description_length == 150
        assert len(catalog.owners) == 1
        assert "Catalog.ВидыНоменклатуры" in catalog.owners[0]

    def test_attributes(self, catalog):
        assert len(catalog.attributes) == 2
        art = catalog.attributes[0]
        assert art.name == "Артикул"
        assert art.synonym == "Артикул"
        assert len(art.type_info) == 1
        assert "Строка" in art.type_info[0]

    def test_tabular_section(self, catalog):
        assert len(catalog.tabular_sections) == 1
        ts = catalog.tabular_sections[0]
        assert ts.name == "Штрихкоды"
        assert ts.synonym == "Штрихкоды"
        assert len(ts.attributes) == 1
        assert ts.attributes[0].name == "Штрихкод"

    def test_object_type_ru(self, catalog):
        assert catalog.object_type_ru == "Справочник"


# === parse_file: Document ===


class TestParseDocument:
    @pytest.fixture()
    def document(self):
        return parse_file(FIXTURES / "Documents" / "TestDocument.xml")

    def test_basic_fields(self, document):
        assert document is not None
        assert document.name == "ПриходнаяНакладная"
        assert document.synonym == "Приходная накладная"
        assert document.object_type == ObjectType.DOCUMENT

    def test_document_specific(self, document):
        assert document.posting == "Allow"
        assert len(document.register_records) == 2
        assert "AccumulationRegister.ОстаткиТоваров" in document.register_records[0]

    def test_attributes(self, document):
        assert len(document.attributes) == 2
        assert document.attributes[0].name == "Контрагент"
        assert document.attributes[1].name == "Сумма"

    def test_tabular_section(self, document):
        assert len(document.tabular_sections) == 1
        ts = document.tabular_sections[0]
        assert ts.name == "Товары"
        assert len(ts.attributes) == 2
        assert ts.attributes[0].name == "Номенклатура"
        assert ts.attributes[1].name == "Количество"


# === parse_file: AccumulationRegister ===


class TestParseAccumulationRegister:
    @pytest.fixture()
    def register(self):
        return parse_file(FIXTURES / "AccumulationRegisters" / "TestAccumReg.xml")

    def test_basic_fields(self, register):
        assert register is not None
        assert register.name == "ОстаткиТоваров"
        assert register.synonym == "Остатки товаров"
        assert register.object_type == ObjectType.ACCUMULATION_REGISTER

    def test_register_type(self, register):
        assert register.register_type == "Balances"

    def test_dimensions(self, register):
        assert len(register.dimensions) == 2
        assert register.dimensions[0].name == "Номенклатура"
        assert register.dimensions[1].name == "Склад"

    def test_resources(self, register):
        assert len(register.resources) == 1
        assert register.resources[0].name == "Количество"


# === parse_file: InformationRegister ===


class TestParseInformationRegister:
    @pytest.fixture()
    def register(self):
        return parse_file(FIXTURES / "InformationRegisters" / "TestInfoReg.xml")

    def test_basic_fields(self, register):
        assert register is not None
        assert register.name == "ЦеныНоменклатуры"
        assert register.synonym == "Цены номенклатуры"
        assert register.object_type == ObjectType.INFORMATION_REGISTER

    def test_register_specific(self, register):
        assert register.periodicity == "Day"
        assert register.write_mode == "Independent"

    def test_dimensions_and_resources(self, register):
        assert len(register.dimensions) == 1
        assert register.dimensions[0].name == "Номенклатура"
        assert len(register.resources) == 1
        assert register.resources[0].name == "Цена"


# === parse_file: AccountingRegister ===


class TestParseAccountingRegister:
    @pytest.fixture()
    def register(self):
        return parse_file(FIXTURES / "AccountingRegisters" / "TestAcctReg.xml")

    def test_basic_fields(self, register):
        assert register is not None
        assert register.name == "Хозрасчетный"
        assert register.object_type == ObjectType.ACCOUNTING_REGISTER

    def test_register_specific(self, register):
        assert register.chart_of_accounts == "ChartOfAccounts.Хозрасчетный"
        assert register.correspondence is True

    def test_dimensions_and_resources(self, register):
        assert len(register.dimensions) == 1
        assert register.dimensions[0].name == "Организация"
        assert len(register.resources) == 1
        assert register.resources[0].name == "Сумма"


# === parse_file: Enum ===


class TestParseEnum:
    @pytest.fixture()
    def enum(self):
        return parse_file(FIXTURES / "Enums" / "TestEnum.xml")

    def test_basic_fields(self, enum):
        assert enum is not None
        assert enum.name == "ВидыОплат"
        assert enum.synonym == "Виды оплат"
        assert enum.comment == "Способы оплаты"
        assert enum.object_type == ObjectType.ENUM

    def test_enum_values(self, enum):
        assert len(enum.enum_values) == 3
        assert enum.enum_values[0].name == "Наличная"
        assert enum.enum_values[0].synonym == "Наличная"
        assert enum.enum_values[0].comment == "Наличный расчёт"
        assert enum.enum_values[1].name == "Безналичная"
        assert enum.enum_values[2].name == "Бартер"


# === parse_directory ===


class TestParseDirectory:
    def test_parse_fixtures_directory(self):
        objects = parse_directory(FIXTURES)
        assert len(objects) == 6

        types = {obj.object_type for obj in objects}
        assert ObjectType.CATALOG in types
        assert ObjectType.DOCUMENT in types
        assert ObjectType.ACCUMULATION_REGISTER in types
        assert ObjectType.INFORMATION_REGISTER in types
        assert ObjectType.ACCOUNTING_REGISTER in types
        assert ObjectType.ENUM in types

    def test_parse_nonexistent_directory(self):
        objects = parse_directory(Path("/nonexistent/path"))
        assert objects == []


# === parse_file: edge cases ===


class TestEdgeCases:
    def test_unsupported_xml(self, tmp_path):
        xml = '<?xml version="1.0"?><MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses"><SomeUnknownType/></MetaDataObject>'
        f = tmp_path / "unknown.xml"
        f.write_text(xml)
        assert parse_file(f) is None


# === Тест на реальных файлах конфигурации ===


REAL_CONFIG = Path(__file__).resolve().parent.parent.parent / "Конфигуратор" / "Prod"


@pytest.mark.skipif(not REAL_CONFIG.exists(), reason="Real config not available")
class TestRealConfig:
    def test_parse_real_catalog(self):
        xml_file = REAL_CONFIG / "Catalogs" / "Pricat_ТребуемоеДействие.xml"
        if xml_file.exists():
            obj = parse_file(xml_file)
            assert obj is not None
            assert obj.name == "Pricat_ТребуемоеДействие"
            assert obj.object_type == ObjectType.CATALOG
            assert obj.code_length == 2
            assert obj.description_length == 25

    def test_parse_real_enum(self):
        xml_file = REAL_CONFIG / "Enums" / "EDI_СостоянияДокументаDESADV.xml"
        if xml_file.exists():
            obj = parse_file(xml_file)
            assert obj is not None
            assert obj.name == "EDI_СостоянияДокументаDESADV"
            assert len(obj.enum_values) == 2

    def test_parse_real_accumulation_register(self):
        xml_file = REAL_CONFIG / "AccumulationRegisters" / "SS_НедостачаКассиров.xml"
        if xml_file.exists():
            obj = parse_file(xml_file)
            assert obj is not None
            assert obj.register_type == "Turnovers"
            assert len(obj.dimensions) == 4
            assert len(obj.resources) == 1
            assert len(obj.attributes) == 3

    def test_parse_real_accounting_register(self):
        xml_file = REAL_CONFIG / "AccountingRegisters" / "СтатьиБаланса.xml"
        if xml_file.exists():
            obj = parse_file(xml_file)
            assert obj is not None
            assert obj.chart_of_accounts == "ChartOfAccounts.СтатьиБаланса"
            assert obj.correspondence is True
            assert len(obj.dimensions) == 3
            assert len(obj.resources) == 2

    def test_parse_all_real_objects(self):
        objects = parse_directory(REAL_CONFIG)
        assert len(objects) > 0
        print(f"\nTotal parsed: {len(objects)} objects")
        by_type = {}
        for obj in objects:
            by_type.setdefault(obj.object_type.value, 0)
            by_type[obj.object_type.value] += 1
        for t, c in sorted(by_type.items()):
            print(f"  {t}: {c}")
