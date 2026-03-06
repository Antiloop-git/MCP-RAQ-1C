"""Маппинг типов 1С из XML-формата в человекочитаемый формат."""

# Маппинг XML-типов в русскоязычные типы 1С
_TYPE_MAP = {
    "xs:string": "Строка",
    "xs:decimal": "Число",
    "xs:boolean": "Булево",
    "xs:dateTime": "Дата",
    "xs:base64Binary": "ХранилищеЗначения",
}

# Маппинг префиксов ссылочных типов
_REF_PREFIX_MAP = {
    "cfg:CatalogRef.": "СправочникСсылка.",
    "cfg:DocumentRef.": "ДокументСсылка.",
    "cfg:EnumRef.": "ПеречислениеСсылка.",
    "cfg:ChartOfCharacteristicTypesRef.": "ПланВидовХарактеристикСсылка.",
    "cfg:ChartOfAccountsRef.": "ПланСчетовСсылка.",
    "cfg:AccumulationRegisterRecordKey.": "РегистрНакопленияКлючЗаписи.",
    "cfg:InformationRegisterRecordKey.": "РегистрСведенийКлючЗаписи.",
    "cfg:AccountingRegisterRecordKey.": "РегистрБухгалтерииКлючЗаписи.",
    "cfg:BusinessProcessRef.": "БизнесПроцессСсылка.",
    "cfg:TaskRef.": "ЗадачаСсылка.",
    "cfg:ExchangePlanRef.": "ПланОбменаСсылка.",
}


def resolve_type(raw_type: str) -> str:
    """Преобразует XML-тип 1С в человекочитаемый формат.

    Примеры:
        "xs:string" -> "Строка"
        "cfg:CatalogRef.Номенклатура" -> "СправочникСсылка.Номенклатура"
        "cfg:EnumRef.ВидыДвижений" -> "ПеречислениеСсылка.ВидыДвижений"
    """
    if raw_type in _TYPE_MAP:
        return _TYPE_MAP[raw_type]

    for xml_prefix, ru_prefix in _REF_PREFIX_MAP.items():
        if raw_type.startswith(xml_prefix):
            return ru_prefix + raw_type[len(xml_prefix):]

    return raw_type


def format_type_with_qualifiers(
    types: list[str],
    string_length: int = 0,
    number_digits: int = 0,
    number_fraction: int = 0,
    date_fractions: str = "",
) -> str:
    """Форматирует тип с квалификаторами.

    Примеры:
        ["Строка"], string_length=50 -> "Строка(50)"
        ["Число"], digits=15, fraction=2 -> "Число(15,2)"
        ["Дата"], date_fractions="Date" -> "Дата(Дата)"
        ["СправочникСсылка.X", "СправочникСсылка.Y"] -> "СправочникСсылка.X | СправочникСсылка.Y"
    """
    if len(types) == 1:
        t = types[0]
        if t == "Строка" and string_length:
            return f"Строка({string_length})"
        if t == "Число" and number_digits:
            return f"Число({number_digits},{number_fraction})"
        if t == "Дата" and date_fractions:
            fractions_ru = {"Date": "Дата", "Time": "Время", "DateTime": "ДатаВремя"}
            return f"Дата({fractions_ru.get(date_fractions, date_fractions)})"
        return t

    return " | ".join(types)
