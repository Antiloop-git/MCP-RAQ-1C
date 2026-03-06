"""Парсер XML-метаданных конфигурации 1С."""

from pathlib import Path

from lxml import etree

from models import (
    EnumValue,
    MetadataAttribute,
    MetadataObject,
    ObjectType,
    PredefinedItem,
    TabularSection,
    URLTemplateInfo,
    WebServiceOperation,
)
from type_resolver import format_type_with_qualifiers, resolve_type

# XML namespaces
NS = {
    "md": "http://v8.1c.ru/8.3/MDClasses",
    "v8": "http://v8.1c.ru/8.1/data/core",
    "xr": "http://v8.1c.ru/8.3/xcf/readable",
    "xs": "http://www.w3.org/2001/XMLSchema",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

NS_PREDEF = {
    "pd": "http://v8.1c.ru/8.3/xcf/predef",
    "v8": "http://v8.1c.ru/8.1/data/core",
    "xs": "http://www.w3.org/2001/XMLSchema",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

# Маппинг корневых тегов XML в ObjectType
_TAG_TO_TYPE = {
    "Catalog": ObjectType.CATALOG,
    "Document": ObjectType.DOCUMENT,
    "AccumulationRegister": ObjectType.ACCUMULATION_REGISTER,
    "InformationRegister": ObjectType.INFORMATION_REGISTER,
    "AccountingRegister": ObjectType.ACCOUNTING_REGISTER,
    "Enum": ObjectType.ENUM,
    "Constant": ObjectType.CONSTANT,
    "DataProcessor": ObjectType.DATA_PROCESSOR,
    "Report": ObjectType.REPORT,
    "ChartOfAccounts": ObjectType.CHART_OF_ACCOUNTS,
    "ChartOfCharacteristicTypes": ObjectType.CHART_OF_CHARACTERISTIC_TYPES,
    "ExchangePlan": ObjectType.EXCHANGE_PLAN,
    "BusinessProcess": ObjectType.BUSINESS_PROCESS,
    "Task": ObjectType.TASK,
    "DefinedType": ObjectType.DEFINED_TYPE,
    "DocumentJournal": ObjectType.DOCUMENT_JOURNAL,
    "CommonModule": ObjectType.COMMON_MODULE,
    "Subsystem": ObjectType.SUBSYSTEM,
    "EventSubscription": ObjectType.EVENT_SUBSCRIPTION,
    "ScheduledJob": ObjectType.SCHEDULED_JOB,
    "HTTPService": ObjectType.HTTP_SERVICE,
    "WebService": ObjectType.WEB_SERVICE,
    "CommonCommand": ObjectType.COMMON_COMMAND,
    "FunctionalOption": ObjectType.FUNCTIONAL_OPTION,
    "CommonAttribute": ObjectType.COMMON_ATTRIBUTE,
    "Role": ObjectType.ROLE,
    "XDTOPackage": ObjectType.XDTO_PACKAGE,
    "SessionParameter": ObjectType.SESSION_PARAMETER,
    "CommonForm": ObjectType.COMMON_FORM,
    "ExternalDataSource": ObjectType.EXTERNAL_DATA_SOURCE,
    "FilterCriterion": ObjectType.FILTER_CRITERION,
    "Sequence": ObjectType.SEQUENCE,
    "FunctionalOptionsParameter": ObjectType.FUNCTIONAL_OPTIONS_PARAMETER,
    "DocumentNumerator": ObjectType.DOCUMENT_NUMERATOR,
    "CommandGroup": ObjectType.COMMAND_GROUP,
    "SettingsStorage": ObjectType.SETTINGS_STORAGE,
}

# Маппинг директорий в ObjectType
DIR_TO_TYPE = {
    "Catalogs": ObjectType.CATALOG,
    "Documents": ObjectType.DOCUMENT,
    "AccumulationRegisters": ObjectType.ACCUMULATION_REGISTER,
    "InformationRegisters": ObjectType.INFORMATION_REGISTER,
    "AccountingRegisters": ObjectType.ACCOUNTING_REGISTER,
    "Enums": ObjectType.ENUM,
    "Constants": ObjectType.CONSTANT,
    "DataProcessors": ObjectType.DATA_PROCESSOR,
    "Reports": ObjectType.REPORT,
    "ChartsOfAccounts": ObjectType.CHART_OF_ACCOUNTS,
    "ChartsOfCharacteristicTypes": ObjectType.CHART_OF_CHARACTERISTIC_TYPES,
    "ExchangePlans": ObjectType.EXCHANGE_PLAN,
    "BusinessProcesses": ObjectType.BUSINESS_PROCESS,
    "Tasks": ObjectType.TASK,
    "DefinedTypes": ObjectType.DEFINED_TYPE,
    "DocumentJournals": ObjectType.DOCUMENT_JOURNAL,
    "CommonModules": ObjectType.COMMON_MODULE,
    "Subsystems": ObjectType.SUBSYSTEM,
    "EventSubscriptions": ObjectType.EVENT_SUBSCRIPTION,
    "ScheduledJobs": ObjectType.SCHEDULED_JOB,
    "HTTPServices": ObjectType.HTTP_SERVICE,
    "WebServices": ObjectType.WEB_SERVICE,
    "CommonCommands": ObjectType.COMMON_COMMAND,
    "FunctionalOptions": ObjectType.FUNCTIONAL_OPTION,
    "CommonAttributes": ObjectType.COMMON_ATTRIBUTE,
    "Roles": ObjectType.ROLE,
    "XDTOPackages": ObjectType.XDTO_PACKAGE,
    "SessionParameters": ObjectType.SESSION_PARAMETER,
    "CommonForms": ObjectType.COMMON_FORM,
    "ExternalDataSources": ObjectType.EXTERNAL_DATA_SOURCE,
    "FilterCriteria": ObjectType.FILTER_CRITERION,
    "Sequences": ObjectType.SEQUENCE,
    "FunctionalOptionsParameters": ObjectType.FUNCTIONAL_OPTIONS_PARAMETER,
    "DocumentNumerators": ObjectType.DOCUMENT_NUMERATOR,
    "CommandGroups": ObjectType.COMMAND_GROUP,
    "SettingsStorages": ObjectType.SETTINGS_STORAGE,
}

# Имена файлов .bsl модулей для поиска
_BSL_MODULE_NAMES = [
    "Module.bsl",
    "ObjectModule.bsl",
    "ManagerModule.bsl",
    "RecordSetModule.bsl",
    "CommandModule.bsl",
    "ValueManagerModule.bsl",
]


def _text(el: etree._Element | None) -> str:
    """Извлечь текст из элемента, пустая строка если None."""
    if el is None:
        return ""
    return (el.text or "").strip()


def _get_synonym(props: etree._Element) -> str:
    """Извлечь русский синоним из Properties/Synonym."""
    for item in props.findall("md:Synonym/v8:item", NS):
        lang = item.findtext("v8:lang", namespaces=NS)
        if lang == "ru":
            return item.findtext("v8:content", default="", namespaces=NS).strip()
    return ""


def _parse_type(type_el: etree._Element | None) -> tuple[list[str], dict]:
    """Парсит элемент Type, возвращает (список типов, квалификаторы)."""
    if type_el is None:
        return [], {}

    raw_types = [t.text for t in type_el.findall("v8:Type", NS) if t.text]
    resolved = [resolve_type(t) for t in raw_types]

    qualifiers = {}

    sq = type_el.find("v8:StringQualifiers", NS)
    if sq is not None:
        length = sq.findtext("v8:Length", namespaces=NS)
        if length and length != "0":
            qualifiers["string_length"] = int(length)

    nq = type_el.find("v8:NumberQualifiers", NS)
    if nq is not None:
        digits = nq.findtext("v8:Digits", namespaces=NS)
        fraction = nq.findtext("v8:FractionDigits", namespaces=NS)
        if digits and digits != "0":
            qualifiers["number_digits"] = int(digits)
            qualifiers["number_fraction"] = int(fraction) if fraction else 0

    dq = type_el.find("v8:DateQualifiers", NS)
    if dq is not None:
        fractions = dq.findtext("v8:DateFractions", namespaces=NS)
        if fractions:
            qualifiers["date_fractions"] = fractions

    return resolved, qualifiers


def _parse_attribute(attr_el: etree._Element) -> MetadataAttribute:
    """Парсит элемент Attribute/Dimension/Resource."""
    props = attr_el.find("md:Properties", NS)
    if props is None:
        props = attr_el.find("Properties")
    if props is None:
        return MetadataAttribute(name="unknown")

    name = _text(props.find("md:Name", NS)) or _text(props.find("Name"))
    synonym = _get_synonym(props)
    type_el = props.find("md:Type", NS)
    if type_el is None:
        type_el = props.find("Type")
    types, qualifiers = _parse_type(type_el)
    type_str = format_type_with_qualifiers(types, **qualifiers) if types else ""

    return MetadataAttribute(
        name=name,
        synonym=synonym,
        type_info=[type_str] if type_str else types,
    )


def _parse_tabular_section(ts_el: etree._Element) -> TabularSection:
    """Парсит TabularSection."""
    props = ts_el.find("md:Properties", NS)
    if props is None:
        props = ts_el.find("Properties")
    if props is None:
        return TabularSection(name="unknown")

    name = _text(props.find("md:Name", NS)) or _text(props.find("Name"))
    synonym = _get_synonym(props)

    attributes = []
    child_objects = ts_el.find("md:ChildObjects", NS)
    if child_objects is None:
        child_objects = ts_el.find("ChildObjects")
    if child_objects is not None:
        for attr_el in child_objects.findall("md:Attribute", NS):
            attributes.append(_parse_attribute(attr_el))

    return TabularSection(name=name, synonym=synonym, attributes=attributes)


def _parse_enum_value(ev_el: etree._Element) -> EnumValue:
    """Парсит EnumValue."""
    props = ev_el.find("md:Properties", NS)
    if props is None:
        props = ev_el.find("Properties")
    if props is None:
        return EnumValue(name="unknown")

    name = _text(props.find("md:Name", NS)) or _text(props.find("Name"))
    synonym = _get_synonym(props)
    comment = _text(props.find("md:Comment", NS)) or _text(props.find("Comment"))

    return EnumValue(name=name, synonym=synonym, comment=comment)


def _parse_url_template(ut_el: etree._Element) -> URLTemplateInfo:
    """Парсит URLTemplate HTTPService."""
    props = ut_el.find("md:Properties", NS)
    if props is None:
        return URLTemplateInfo(name="unknown")

    name = _text(props.find("md:Name", NS))
    synonym = _get_synonym(props)
    template = _text(props.find("md:Template", NS))

    methods = []
    child_objects = ut_el.find("md:ChildObjects", NS)
    if child_objects is not None:
        for method_el in child_objects.findall("md:Method", NS):
            m_props = method_el.find("md:Properties", NS)
            if m_props is not None:
                http_method = _text(m_props.find("md:HTTPMethod", NS))
                if http_method:
                    methods.append(http_method)

    return URLTemplateInfo(name=name, synonym=synonym, template=template, methods=methods)


def _parse_ws_operation(op_el: etree._Element) -> WebServiceOperation:
    """Парсит Operation WebService."""
    props = op_el.find("md:Properties", NS)
    if props is None:
        return WebServiceOperation(name="unknown")

    name = _text(props.find("md:Name", NS))
    synonym = _get_synonym(props)
    procedure_name = _text(props.find("md:ProcedureName", NS))
    return_type = _text(props.find("md:XDTOReturningValueType", NS))

    parameters = []
    child_objects = op_el.find("md:ChildObjects", NS)
    if child_objects is not None:
        for param_el in child_objects.findall("md:Parameter", NS):
            p_props = param_el.find("md:Properties", NS)
            if p_props is not None:
                p_name = _text(p_props.find("md:Name", NS))
                p_synonym = _get_synonym(p_props)
                p_type = _text(p_props.find("md:XDTOValueType", NS))
                direction = _text(p_props.find("md:TransferDirection", NS))
                parameters.append(MetadataAttribute(
                    name=p_name, synonym=p_synonym,
                    type_info=[p_type] if p_type else [],
                    comment=direction,
                ))

    return WebServiceOperation(
        name=name, synonym=synonym,
        procedure_name=procedure_name, return_type=return_type,
        parameters=parameters,
    )


def _read_bsl_modules(obj_dir: Path) -> dict[str, str]:
    """Читает .bsl модули из подпапки Ext/ объекта."""
    modules = {}
    ext_dir = obj_dir / "Ext"
    if not ext_dir.exists():
        return modules

    for bsl_name in _BSL_MODULE_NAMES:
        bsl_path = ext_dir / bsl_name
        if bsl_path.exists():
            try:
                code = bsl_path.read_text(encoding="utf-8-sig").strip()
                if code:
                    key = bsl_name.replace(".bsl", "")
                    modules[key] = code
            except Exception:
                pass
    return modules


def _parse_predefined(obj_dir: Path) -> list[PredefinedItem]:
    """Парсит Ext/Predefined.xml — предопределённые элементы."""
    predef_path = obj_dir / "Ext" / "Predefined.xml"
    if not predef_path.exists():
        return []

    items = []
    try:
        tree = etree.parse(predef_path)
        root = tree.getroot()
        # Рекурсивно собираем все Item
        _collect_predefined_items(root, items)
    except Exception:
        pass
    return items


def _collect_predefined_items(
    el: etree._Element, items: list[PredefinedItem],
) -> None:
    """Рекурсивно собирает предопределённые элементы из Item и ChildItems."""
    ns = "http://v8.1c.ru/8.3/xcf/predef"
    for item_el in el:
        tag = etree.QName(item_el).localname
        if tag != "Item":
            continue

        name = ""
        code = ""
        description = ""
        for child in item_el:
            child_tag = etree.QName(child).localname
            if child_tag == "Name":
                name = (child.text or "").strip()
            elif child_tag == "Code":
                code = (child.text or "").strip()
            elif child_tag == "Description":
                description = (child.text or "").strip()
            elif child_tag == "ChildItems":
                _collect_predefined_items(child, items)

        if name:
            items.append(PredefinedItem(name=name, code=code, description=description))


def _parse_subsystems_recursive(
    subsystems_dir: Path, objects: list[MetadataObject],
) -> None:
    """Рекурсивно парсит подсистемы из вложенных директорий Subsystems/."""
    if not subsystems_dir.exists():
        return

    for xml_file in sorted(subsystems_dir.glob("*.xml")):
        try:
            obj = parse_file(xml_file)
            if obj is not None:
                # Ищем вложенные подсистемы
                sub_dir = subsystems_dir / xml_file.stem / "Subsystems"
                if sub_dir.exists():
                    nested = []
                    _parse_subsystems_recursive(sub_dir, nested)
                    obj.child_subsystems = [n.name for n in nested]
                    objects.extend(nested)
                objects.append(obj)
        except Exception as e:
            print(f"Warning: failed to parse {xml_file.name}: {e}")


def parse_file(filepath: Path) -> MetadataObject | None:
    """Парсит один XML-файл метаданных 1С.

    Returns:
        MetadataObject или None если файл не является поддерживаемым типом.
    """
    tree = etree.parse(filepath)
    root = tree.getroot()

    obj_el = None
    obj_type = None
    for child in root:
        tag = etree.QName(child).localname
        if tag in _TAG_TO_TYPE:
            obj_el = child
            obj_type = _TAG_TO_TYPE[tag]
            break

    if obj_el is None or obj_type is None:
        return None

    props = obj_el.find("md:Properties", NS)
    if props is None:
        return None

    name = _text(props.find("md:Name", NS))
    synonym = _get_synonym(props)
    comment = _text(props.find("md:Comment", NS))

    obj = MetadataObject(
        name=name,
        synonym=synonym,
        comment=comment,
        object_type=obj_type,
    )

    # === Catalog ===
    if obj_type == ObjectType.CATALOG:
        obj.hierarchical = _text(props.find("md:Hierarchical", NS)) == "true"
        code_len = _text(props.find("md:CodeLength", NS))
        desc_len = _text(props.find("md:DescriptionLength", NS))
        obj.code_length = int(code_len) if code_len else 0
        obj.description_length = int(desc_len) if desc_len else 0
        for owner in props.findall("md:Owners/xr:Item", NS):
            if owner.text:
                obj.owners.append(owner.text)

    # === Document ===
    if obj_type == ObjectType.DOCUMENT:
        obj.posting = _text(props.find("md:Posting", NS))
        for rr in props.findall("md:RegisterRecords/xr:Item", NS):
            if rr.text:
                obj.register_records.append(rr.text)

    # === AccumulationRegister ===
    if obj_type == ObjectType.ACCUMULATION_REGISTER:
        obj.register_type = _text(props.find("md:RegisterType", NS))

    # === InformationRegister ===
    if obj_type == ObjectType.INFORMATION_REGISTER:
        obj.periodicity = _text(props.find("md:InformationRegisterPeriodicity", NS))
        obj.write_mode = _text(props.find("md:WriteMode", NS))

    # === AccountingRegister ===
    if obj_type == ObjectType.ACCOUNTING_REGISTER:
        obj.chart_of_accounts = _text(props.find("md:ChartOfAccounts", NS))
        obj.correspondence = _text(props.find("md:Correspondence", NS)) == "true"

    # === Constant / DefinedType / SessionParameter / CommonAttribute ===
    if obj_type in (
        ObjectType.CONSTANT, ObjectType.DEFINED_TYPE,
        ObjectType.SESSION_PARAMETER, ObjectType.COMMON_ATTRIBUTE,
    ):
        type_el = props.find("md:Type", NS)
        types, qualifiers = _parse_type(type_el)
        type_str = format_type_with_qualifiers(types, **qualifiers) if types else ""
        obj.type_info = [type_str] if type_str else types

    # === ChartOfAccounts / ChartOfCharacteristicTypes ===
    if obj_type in (ObjectType.CHART_OF_ACCOUNTS, ObjectType.CHART_OF_CHARACTERISTIC_TYPES):
        code_len = _text(props.find("md:CodeLength", NS))
        desc_len = _text(props.find("md:DescriptionLength", NS))
        obj.code_length = int(code_len) if code_len else 0
        obj.description_length = int(desc_len) if desc_len else 0

    # === ExchangePlan ===
    if obj_type == ObjectType.EXCHANGE_PLAN:
        code_len = _text(props.find("md:CodeLength", NS))
        desc_len = _text(props.find("md:DescriptionLength", NS))
        obj.code_length = int(code_len) if code_len else 0
        obj.description_length = int(desc_len) if desc_len else 0

    # === DocumentJournal ===
    if obj_type == ObjectType.DOCUMENT_JOURNAL:
        for rd in props.findall("md:RegisteredDocuments/xr:Item", NS):
            if rd.text:
                obj.registered_documents.append(rd.text)

    # === CommonModule ===
    if obj_type == ObjectType.COMMON_MODULE:
        obj.global_module = _text(props.find("md:Global", NS)) == "true"
        obj.server = _text(props.find("md:Server", NS)) == "true"
        obj.client = _text(props.find("md:ClientManagedApplication", NS)) == "true"
        obj.external_connection = _text(props.find("md:ExternalConnection", NS)) == "true"
        obj.server_call = _text(props.find("md:ServerCall", NS)) == "true"
        obj.privileged = _text(props.find("md:Privileged", NS)) == "true"
        obj.return_values_reuse = _text(props.find("md:ReturnValuesReuse", NS))

    # === Subsystem ===
    if obj_type == ObjectType.SUBSYSTEM:
        obj.include_in_command_interface = (
            _text(props.find("md:IncludeInCommandInterface", NS)) == "true"
        )
        for item in props.findall("md:Content/xr:Item", NS):
            if item.text:
                obj.content.append(item.text)

    # === EventSubscription ===
    if obj_type == ObjectType.EVENT_SUBSCRIPTION:
        source_el = props.find("md:Source", NS)
        if source_el is not None:
            for t in source_el.findall("v8:Type", NS):
                if t.text:
                    obj.source_types.append(resolve_type(t.text))
        obj.event = _text(props.find("md:Event", NS))
        obj.handler = _text(props.find("md:Handler", NS))

    # === ScheduledJob ===
    if obj_type == ObjectType.SCHEDULED_JOB:
        obj.method_name = _text(props.find("md:MethodName", NS))

    # === HTTPService ===
    if obj_type == ObjectType.HTTP_SERVICE:
        obj.root_url = _text(props.find("md:RootURL", NS))

    # === WebService ===
    if obj_type == ObjectType.WEB_SERVICE:
        obj.namespace = _text(props.find("md:Namespace", NS))

    # === CommonCommand ===
    if obj_type == ObjectType.COMMON_COMMAND:
        obj.group = _text(props.find("md:Group", NS))
        obj.modifies_data = _text(props.find("md:ModifiesData", NS)) == "true"

    # === FunctionalOption ===
    if obj_type == ObjectType.FUNCTIONAL_OPTION:
        obj.location = _text(props.find("md:Location", NS))
        for item in props.findall("md:Content/xr:Object", NS):
            if item.text:
                obj.content.append(item.text)

    # === XDTOPackage ===
    if obj_type == ObjectType.XDTO_PACKAGE:
        obj.namespace = _text(props.find("md:Namespace", NS))

    # === FilterCriterion ===
    if obj_type == ObjectType.FILTER_CRITERION:
        type_el = props.find("md:Type", NS)
        types, qualifiers = _parse_type(type_el)
        type_str = format_type_with_qualifiers(types, **qualifiers) if types else ""
        obj.type_info = [type_str] if type_str else types
        for item in props.findall("md:Content/xr:Item", NS):
            if item.text:
                obj.content.append(item.text)

    # === Sequence ===
    if obj_type == ObjectType.SEQUENCE:
        for item in props.findall("md:Documents/xr:Item", NS):
            if item.text:
                obj.documents.append(item.text)

    # === FunctionalOptionsParameter ===
    if obj_type == ObjectType.FUNCTIONAL_OPTIONS_PARAMETER:
        for item in props.findall("md:Use/xr:Item", NS):
            if item.text:
                obj.use.append(item.text)

    # === DocumentNumerator ===
    if obj_type == ObjectType.DOCUMENT_NUMERATOR:
        obj.number_type = _text(props.find("md:NumberType", NS))
        num_len = _text(props.find("md:NumberLength", NS))
        obj.number_length = int(num_len) if num_len else 0
        obj.number_periodicity = _text(props.find("md:NumberPeriodicity", NS))

    # === CommandGroup ===
    if obj_type == ObjectType.COMMAND_GROUP:
        obj.category = _text(props.find("md:Category", NS))

    # === ChildObjects ===
    child_objects = obj_el.find("md:ChildObjects", NS)
    if child_objects is not None:
        for attr_el in child_objects.findall("md:Attribute", NS):
            obj.attributes.append(_parse_attribute(attr_el))

        for ts_el in child_objects.findall("md:TabularSection", NS):
            obj.tabular_sections.append(_parse_tabular_section(ts_el))

        for dim_el in child_objects.findall("md:Dimension", NS):
            obj.dimensions.append(_parse_attribute(dim_el))

        for res_el in child_objects.findall("md:Resource", NS):
            obj.resources.append(_parse_attribute(res_el))

        for ev_el in child_objects.findall("md:EnumValue", NS):
            obj.enum_values.append(_parse_enum_value(ev_el))

        for col_el in child_objects.findall("md:Column", NS):
            obj.attributes.append(_parse_attribute(col_el))

        for ut_el in child_objects.findall("md:URLTemplate", NS):
            obj.url_templates.append(_parse_url_template(ut_el))

        for op_el in child_objects.findall("md:Operation", NS):
            obj.operations.append(_parse_ws_operation(op_el))

    # === .bsl модули и предопределённые ===
    # Определяем директорию объекта (рядом с XML есть папка с тем же именем)
    obj_dir = filepath.parent / filepath.stem
    if obj_dir.is_dir():
        obj.modules = _read_bsl_modules(obj_dir)
        obj.predefined = _parse_predefined(obj_dir)

    return obj


def parse_directory(config_path: Path) -> list[MetadataObject]:
    """Парсит все XML-файлы из директории конфигурации."""
    objects = []

    for dir_name, obj_type in DIR_TO_TYPE.items():
        dir_path = config_path / dir_name
        if not dir_path.exists():
            continue

        # Подсистемы парсим рекурсивно
        if obj_type == ObjectType.SUBSYSTEM:
            _parse_subsystems_recursive(dir_path, objects)
            continue

        for xml_file in sorted(dir_path.glob("*.xml")):
            try:
                obj = parse_file(xml_file)
                if obj is not None:
                    objects.append(obj)
            except Exception as e:
                print(f"Warning: failed to parse {xml_file.name}: {e}")

    return objects
