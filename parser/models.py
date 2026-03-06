"""Pydantic-модели для метаданных 1С."""

from enum import Enum
from pydantic import BaseModel, Field


class ObjectType(str, Enum):
    CATALOG = "Catalog"
    DOCUMENT = "Document"
    ACCUMULATION_REGISTER = "AccumulationRegister"
    INFORMATION_REGISTER = "InformationRegister"
    ACCOUNTING_REGISTER = "AccountingRegister"
    ENUM = "Enum"
    CONSTANT = "Constant"
    DATA_PROCESSOR = "DataProcessor"
    REPORT = "Report"
    CHART_OF_ACCOUNTS = "ChartOfAccounts"
    CHART_OF_CHARACTERISTIC_TYPES = "ChartOfCharacteristicTypes"
    EXCHANGE_PLAN = "ExchangePlan"
    BUSINESS_PROCESS = "BusinessProcess"
    TASK = "Task"
    DEFINED_TYPE = "DefinedType"
    DOCUMENT_JOURNAL = "DocumentJournal"
    COMMON_MODULE = "CommonModule"
    SUBSYSTEM = "Subsystem"
    EVENT_SUBSCRIPTION = "EventSubscription"
    SCHEDULED_JOB = "ScheduledJob"
    HTTP_SERVICE = "HTTPService"
    WEB_SERVICE = "WebService"
    COMMON_COMMAND = "CommonCommand"
    FUNCTIONAL_OPTION = "FunctionalOption"
    COMMON_ATTRIBUTE = "CommonAttribute"
    ROLE = "Role"
    XDTO_PACKAGE = "XDTOPackage"
    SESSION_PARAMETER = "SessionParameter"
    COMMON_FORM = "CommonForm"
    EXTERNAL_DATA_SOURCE = "ExternalDataSource"
    FILTER_CRITERION = "FilterCriterion"
    SEQUENCE = "Sequence"
    FUNCTIONAL_OPTIONS_PARAMETER = "FunctionalOptionsParameter"
    DOCUMENT_NUMERATOR = "DocumentNumerator"
    COMMAND_GROUP = "CommandGroup"
    SETTINGS_STORAGE = "SettingsStorage"


OBJECT_TYPE_RU = {
    ObjectType.CATALOG: "Справочник",
    ObjectType.DOCUMENT: "Документ",
    ObjectType.ACCUMULATION_REGISTER: "РегистрНакопления",
    ObjectType.INFORMATION_REGISTER: "РегистрСведений",
    ObjectType.ACCOUNTING_REGISTER: "РегистрБухгалтерии",
    ObjectType.ENUM: "Перечисление",
    ObjectType.CONSTANT: "Константа",
    ObjectType.DATA_PROCESSOR: "Обработка",
    ObjectType.REPORT: "Отчет",
    ObjectType.CHART_OF_ACCOUNTS: "ПланСчетов",
    ObjectType.CHART_OF_CHARACTERISTIC_TYPES: "ПланВидовХарактеристик",
    ObjectType.EXCHANGE_PLAN: "ПланОбмена",
    ObjectType.BUSINESS_PROCESS: "БизнесПроцесс",
    ObjectType.TASK: "Задача",
    ObjectType.DEFINED_TYPE: "ОпределяемыйТип",
    ObjectType.DOCUMENT_JOURNAL: "ЖурналДокументов",
    ObjectType.COMMON_MODULE: "ОбщийМодуль",
    ObjectType.SUBSYSTEM: "Подсистема",
    ObjectType.EVENT_SUBSCRIPTION: "ПодпискаНаСобытие",
    ObjectType.SCHEDULED_JOB: "РегламентноеЗадание",
    ObjectType.HTTP_SERVICE: "HTTPСервис",
    ObjectType.WEB_SERVICE: "WebСервис",
    ObjectType.COMMON_COMMAND: "ОбщаяКоманда",
    ObjectType.FUNCTIONAL_OPTION: "ФункциональнаяОпция",
    ObjectType.COMMON_ATTRIBUTE: "ОбщийРеквизит",
    ObjectType.ROLE: "Роль",
    ObjectType.XDTO_PACKAGE: "ПакетXDTO",
    ObjectType.SESSION_PARAMETER: "ПараметрСеанса",
    ObjectType.COMMON_FORM: "ОбщаяФорма",
    ObjectType.EXTERNAL_DATA_SOURCE: "ВнешнийИсточникДанных",
    ObjectType.FILTER_CRITERION: "КритерийОтбора",
    ObjectType.SEQUENCE: "Последовательность",
    ObjectType.FUNCTIONAL_OPTIONS_PARAMETER: "ПараметрФункциональныхОпций",
    ObjectType.DOCUMENT_NUMERATOR: "НумераторДокументов",
    ObjectType.COMMAND_GROUP: "ГруппаКоманд",
    ObjectType.SETTINGS_STORAGE: "ХранилищеНастроек",
}


class RegisterType(str, Enum):
    TURNOVERS = "Turnovers"
    BALANCES = "Balances"


class Periodicity(str, Enum):
    NONPERIODICAL = "Nonperiodical"
    DAY = "Day"
    MONTH = "Month"
    QUARTER = "Quarter"
    YEAR = "Year"


class MetadataAttribute(BaseModel):
    """Реквизит объекта метаданных (Attribute, Dimension, Resource)."""

    name: str
    synonym: str = ""
    type_info: list[str] = Field(default_factory=list)
    comment: str = ""


class EnumValue(BaseModel):
    """Значение перечисления."""

    name: str
    synonym: str = ""
    comment: str = ""


class TabularSection(BaseModel):
    """Табличная часть объекта метаданных."""

    name: str
    synonym: str = ""
    attributes: list[MetadataAttribute] = Field(default_factory=list)


class URLTemplateInfo(BaseModel):
    """URL-шаблон HTTPService."""

    name: str
    synonym: str = ""
    template: str = ""
    methods: list[str] = Field(default_factory=list)


class WebServiceOperation(BaseModel):
    """Операция WebService."""

    name: str
    synonym: str = ""
    procedure_name: str = ""
    return_type: str = ""
    parameters: list[MetadataAttribute] = Field(default_factory=list)


class PredefinedItem(BaseModel):
    """Предопределённый элемент."""

    name: str
    code: str = ""
    description: str = ""


class MetadataObject(BaseModel):
    """Объект метаданных 1С."""

    name: str
    synonym: str = ""
    comment: str = ""
    object_type: ObjectType
    object_type_ru: str = ""

    # Catalog
    hierarchical: bool = False
    owners: list[str] = Field(default_factory=list)
    code_length: int = 0
    description_length: int = 0

    # Document
    posting: str = ""  # Allow, Deny
    register_records: list[str] = Field(default_factory=list)

    # AccumulationRegister
    register_type: str = ""  # Turnovers, Balances

    # InformationRegister
    periodicity: str = ""  # Nonperiodical, Day, Month, Year
    write_mode: str = ""  # Independent, Slave

    # AccountingRegister
    chart_of_accounts: str = ""
    correspondence: bool = False

    # Constant / DefinedType / SessionParameter / CommonAttribute / FilterCriterion
    type_info: list[str] = Field(default_factory=list)

    # DocumentJournal
    registered_documents: list[str] = Field(default_factory=list)

    # CommonModule
    server: bool = False
    client: bool = False
    server_call: bool = False
    privileged: bool = False
    global_module: bool = False
    external_connection: bool = False
    return_values_reuse: str = ""  # DontUse, DuringRequest, DuringSession

    # Subsystem / FunctionalOption / FilterCriterion
    content: list[str] = Field(default_factory=list)
    include_in_command_interface: bool = False
    child_subsystems: list[str] = Field(default_factory=list)

    # EventSubscription
    source_types: list[str] = Field(default_factory=list)
    event: str = ""
    handler: str = ""

    # ScheduledJob
    method_name: str = ""

    # HTTPService
    root_url: str = ""
    url_templates: list[URLTemplateInfo] = Field(default_factory=list)

    # WebService / XDTOPackage
    namespace: str = ""
    operations: list[WebServiceOperation] = Field(default_factory=list)

    # CommonCommand / CommandGroup
    group: str = ""
    command_parameter_type: str = ""
    modifies_data: bool = False
    category: str = ""

    # FunctionalOption
    location: str = ""

    # FunctionalOptionsParameter
    use: list[str] = Field(default_factory=list)

    # Sequence
    documents: list[str] = Field(default_factory=list)

    # DocumentNumerator
    number_type: str = ""
    number_length: int = 0
    number_periodicity: str = ""

    # Код модулей (.bsl)
    modules: dict[str, str] = Field(default_factory=dict)

    # Предопределённые элементы
    predefined: list[PredefinedItem] = Field(default_factory=list)

    # Общие дочерние объекты
    attributes: list[MetadataAttribute] = Field(default_factory=list)
    tabular_sections: list[TabularSection] = Field(default_factory=list)
    dimensions: list[MetadataAttribute] = Field(default_factory=list)
    resources: list[MetadataAttribute] = Field(default_factory=list)
    enum_values: list[EnumValue] = Field(default_factory=list)

    def model_post_init(self, __context) -> None:
        if not self.object_type_ru:
            self.object_type_ru = OBJECT_TYPE_RU.get(self.object_type, "")
