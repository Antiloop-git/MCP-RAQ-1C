# MCP RAQ 1C — Инструкция для LLM-агентов

Этот MCP-сервер предоставляет 9 инструментов для работы с метаданными и данными конфигурации 1С.
Используй их, чтобы узнать структуру объектов, зависимости, подсистемы, код и живые данные.

## Доступные инструменты

### Поиск метаданных

#### 1c_metadata_search
Гибридный поиск объектов метаданных по текстовому запросу (по имени, синониму и описанию).

- `query` (string) — поисковый запрос
- `object_type` (string, опциональный) — фильтр: Catalog, Document, AccumulationRegister, InformationRegister, AccountingRegister, Enum, CommonModule, Subsystem и др. (36 типов)
- `limit` (number, по умолчанию 10, макс 50)

Возвращает компактный список: имя, синоним, тип, score.

```
1c_metadata_search(query: "заказ клиента")
1c_metadata_search(query: "остатки товаров", object_type: "AccumulationRegister")
```

#### 1c_metadata_details
Полное описание объекта: реквизиты, табличные части, измерения, ресурсы, движения регистров.

- `name` (string) — техническое имя объекта

```
1c_metadata_details(name: "SS_ЗаказКлиента")
1c_metadata_details(name: "Номенклатура")
```

#### 1c_metadata_types
Статистика по типам объектов: сколько справочников, документов, регистров.

Без параметров.

### Поиск кода

#### 1c_code_search
Поиск по BSL-коду модулей конфигурации (процедуры, функции, фрагменты кода).

- `query` (string) — поисковый запрос (описание логики или имя процедуры)
- `object_name` (string, опциональный) — фильтр по имени объекта
- `object_type` (string, опциональный) — фильтр по типу объекта
- `limit` (number, по умолчанию 5, макс 20)

Возвращает: путь к файлу, тип модуля, имя процедуры, фрагмент кода.

```
1c_code_search(query: "расчёт себестоимости")
1c_code_search(query: "ОбработкаПроведения", object_name: "ПриходнаяНакладная")
```

### Зависимости и навигация

#### 1c_dependencies
Граф зависимостей между документами и регистрами: какие документы пишут в регистр, в какие регистры пишет документ.

- `name` (string) — имя документа или регистра
- `direction` (enum: forward/reverse/all, по умолчанию all)
  - forward — документ → его регистры
  - reverse — регистр → документы, которые в него пишут
  - all — все связи объекта

```
1c_dependencies(name: "УчетПартий", direction: "reverse")
1c_dependencies(name: "ПриходнаяНакладная", direction: "forward")
1c_dependencies(name: "ДвижениеТМЦ")
```

#### 1c_subsystems
Навигация по подсистемам (бизнес-модулям) конфигурации.

- `action` (enum: tree/content/find)
  - tree — дерево подсистем верхнего уровня
  - content — объекты конкретной подсистемы
  - find — в каких подсистемах находится объект
- `name` (string, обязательно для content и find) — имя подсистемы или объекта
- `recursive` (boolean, по умолчанию false) — включать вложенные подсистемы

```
1c_subsystems(action: "tree")
1c_subsystems(action: "content", name: "Продажи")
1c_subsystems(action: "content", name: "Продажи", recursive: true)
1c_subsystems(action: "find", name: "Номенклатура")
```

### OData — живые данные из 1С

Эти инструменты доступны, только если настроено подключение к OData-интерфейсу 1С.

#### 1c_odata_query
Универсальный запрос к OData-интерфейсу 1С. Читает данные справочников, документов, регистров.

- `entity_set` (string) — набор данных: Catalog_Номенклатура, Document_ПриходнаяНакладная, AccumulationRegister_УчетПартий и т.д.
- `filter` (string, опциональный) — OData $filter
- `select` (string, опциональный) — поля через запятую
- `top` (number, по умолчанию 100, макс 1000)
- `orderby` (string, опциональный)

```
1c_odata_query(entity_set: "Catalog_Номенклатура", top: 5)
1c_odata_query(entity_set: "Catalog_Склады")
```

#### 1c_register_balances
Остатки и обороты регистров накопления через виртуальные таблицы OData.

- `register_name` (string) — имя регистра
- `table_type` (enum: Balance/Turnovers/BalanceAndTurnovers/RecordType)
- `filter` (string, опциональный)
- `select` (string, опциональный)
- `top` (number, по умолчанию 100)

```
1c_register_balances(register_name: "УчетПартий", table_type: "Balance", top: 10)
```

#### 1c_register_movements
Движения регистра накопления за период. Показывает документы-регистраторы.

- `register_name` (string) — имя регистра
- `filter` (string) — обязательный OData $filter (период, номенклатура и т.д.)
- `select` (string, опциональный)
- `top` (number, по умолчанию 100)

```
1c_register_movements(register_name: "ДвижениеТМЦ", filter: "Period ge datetime'2025-01-01T00:00:00'")
```

## Рекомендуемый workflow

### Для разработчика 1С
1. **Поиск** → `1c_metadata_search` — найти объект по описанию
2. **Зависимости** → `1c_dependencies` — понять связи с другими объектами
3. **Подсистемы** → `1c_subsystems(action: "find")` — понять роль объекта в бизнесе
4. **Детали** → `1c_metadata_details` — получить структуру (реквизиты, ТЧ, регистры)
5. **Код** → `1c_code_search` — найти существующий код для примера
6. **Написание** — использовать полученную информацию для кода

### Для аналитика 1С
1. **Поиск** → `1c_metadata_search` — найти нужные объекты
2. **Данные** → `1c_odata_query` / `1c_register_balances` / `1c_register_movements`
3. **Анализ** — интерпретация полученных данных

### Пример: «Какие документы пишут в регистр УчетПартий?»
```
Шаг 1: 1c_dependencies(name: "УчетПартий", direction: "reverse")
        → Список документов: ПриходнаяНакладная, РасходнаяНакладная, ...

Шаг 2: 1c_metadata_details(name: "ПриходнаяНакладная")
        → Структура документа, его реквизиты и движения

Шаг 3: 1c_code_search(query: "ОбработкаПроведения", object_name: "ПриходнаяНакладная")
        → Код проведения документа
```

## Советы

- Ищи по **синониму** на русском: "контрагенты", "заказ клиента"
- Ищи по **техническому имени**: "SS_ЗаказКлиента", "EDIПровайдеры"
- Префиксы в именах: `SS_`, `Смолл_`, `пэм` — часть конфигурации
- Используй `1c_subsystems(action: "tree")` для обзора бизнес-структуры конфигурации
- Используй `1c_dependencies` перед изменением объектов — чтобы понять что затронется
