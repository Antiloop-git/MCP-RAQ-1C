"""FastAPI-приложение парсера метаданных 1С."""

from pathlib import Path

from fastapi import FastAPI, HTTPException

from config import CONFIG_PATH
from models import MetadataObject, ObjectType
from xml_parser import DIR_TO_TYPE, parse_directory, parse_file

app = FastAPI(title="1C Metadata Parser", version="0.1.0")

# Кеш: список всех объектов
_cache: list[MetadataObject] = []
# Индекс: {object_type: {name: [MetadataObject, ...]}}
_index: dict[ObjectType, dict[str, list[MetadataObject]]] = {}


def _ensure_cache() -> None:
    """Парсит конфигурацию и заполняет кеш, если ещё не заполнен."""
    if _cache:
        return
    objects = parse_directory(CONFIG_PATH)
    _cache.extend(objects)
    for obj in objects:
        _index.setdefault(obj.object_type, {}).setdefault(obj.name, []).append(obj)


def _invalidate_cache() -> None:
    _cache.clear()
    _index.clear()


# --- Маппинг имён типов (английских) в ObjectType ---
_TYPE_NAME_MAP: dict[str, ObjectType] = {
    t.value.lower(): t for t in ObjectType
}


def _resolve_object_type(object_type: str) -> ObjectType:
    key = object_type.lower()
    if key in _TYPE_NAME_MAP:
        return _TYPE_NAME_MAP[key]
    # Попробуем по русским именам и множественным формам директорий
    dir_lower = {k.lower(): v for k, v in DIR_TO_TYPE.items()}
    if key in dir_lower:
        return dir_lower[key]
    raise HTTPException(status_code=404, detail=f"Unknown object type: {object_type}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/parse/all", response_model=list[MetadataObject])
def parse_all():
    """Возвращает все распарсенные объекты метаданных."""
    _ensure_cache()
    return _cache


@app.get("/parse/{object_type}", response_model=list[MetadataObject])
def parse_by_type(object_type: str):
    """Возвращает все объекты указанного типа."""
    _ensure_cache()
    ot = _resolve_object_type(object_type)
    objects = _index.get(ot, {})
    result = []
    for obj_list in objects.values():
        result.extend(obj_list)
    return result


@app.get("/parse/{object_type}/{object_name}", response_model=list[MetadataObject])
def parse_one(object_type: str, object_name: str):
    """Возвращает объект(ы) по типу и имени."""
    _ensure_cache()
    ot = _resolve_object_type(object_type)
    objects = _index.get(ot, {})
    if object_name not in objects:
        available = list(objects.keys())[:10]
        raise HTTPException(
            status_code=404,
            detail=f"Object '{object_name}' not found. Available: {available}",
        )
    return objects[object_name]


@app.get("/stats")
def stats():
    """Статистика по типам объектов."""
    _ensure_cache()
    return {
        ot.value: sum(len(lst) for lst in objs.values())
        for ot, objs in _index.items()
    }


@app.get("/config-path")
def get_config_path():
    """Возвращает текущий путь к XML-выгрузке."""
    return {"config_path": str(CONFIG_PATH)}


@app.post("/reload")
def reload(config_path: str | None = None):
    """Сбрасывает кеш и перечитывает конфигурацию.

    Args:
        config_path: новый путь к XML-выгрузке (query parameter, опционально).
    """
    global CONFIG_PATH
    if config_path:
        import config as cfg

        new_path = Path(config_path)
        if not new_path.is_dir():
            raise HTTPException(
                status_code=400, detail=f"Путь не найден: {config_path}"
            )
        cfg.CONFIG_PATH = new_path
        CONFIG_PATH = new_path
    _invalidate_cache()
    _ensure_cache()
    return {
        "status": "reloaded",
        "total_objects": len(_cache),
        "config_path": str(CONFIG_PATH),
    }


if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT

    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
