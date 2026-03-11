"""Экспорт всех метаданных конфигурации 1С в JSON."""

import json
import sys
from pathlib import Path

from xml_parser import parse_directory


def export(config_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Парсинг конфигурации: {config_path}")
    objects = parse_directory(config_path)
    print(f"Распарсено объектов: {len(objects)}")

    # Статистика
    by_type: dict[str, int] = {}
    for obj in objects:
        by_type.setdefault(obj.object_type.value, 0)
        by_type[obj.object_type.value] += 1

    for t, c in sorted(by_type.items()):
        print(f"  {t}: {c}")

    # Сохраняем модули (.bsl) отдельно, чтобы не раздувать основные JSON
    modules_dir = output_dir / "modules"
    modules_dir.mkdir(exist_ok=True)
    modules_count = 0
    for obj in objects:
        if obj.modules:
            obj_module_dir = modules_dir / obj.object_type.value
            obj_module_dir.mkdir(exist_ok=True)
            for module_name, code in obj.modules.items():
                bsl_file = obj_module_dir / f"{obj.name}.{module_name}.bsl"
                bsl_file.write_text(code, encoding="utf-8")
                modules_count += 1

    # Сохраняем всё в один файл (без кода модулей для компактности)
    all_data = [obj.model_dump(mode="json", exclude={"modules"}) for obj in objects]
    all_file = output_dir / "all_metadata.json"
    all_file.write_text(json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nВсе объекты (без кода): {all_file} ({len(all_data)} шт.)")

    # Полная версия с кодом — отдельный файл
    all_full = [obj.model_dump(mode="json") for obj in objects]
    full_file = output_dir / "all_metadata_full.json"
    full_file.write_text(json.dumps(all_full, ensure_ascii=False, indent=2), encoding="utf-8")
    sz_mb = full_file.stat().st_size / 1024 / 1024
    print(f"Полная версия (с кодом): {full_file} ({sz_mb:.1f} MB)")

    # Сохраняем по типам (без кода модулей)
    by_type_objects: dict[str, list] = {}
    for obj in objects:
        key = obj.object_type.value
        by_type_objects.setdefault(key, []).append(
            obj.model_dump(mode="json", exclude={"modules"})
        )

    for type_name, type_objects in sorted(by_type_objects.items()):
        type_file = output_dir / f"{type_name}.json"
        type_file.write_text(json.dumps(type_objects, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {type_file.name}: {len(type_objects)} шт.")

    print(f"\n.bsl модулей: {modules_count} файлов в {modules_dir}/")
    print(f"Предопределённых элементов: {sum(len(o.predefined) for o in objects)}")
    print(f"Подсистем (с вложенными): {sum(1 for o in objects if o.object_type.value == 'Subsystem')}")
    print(f"\nГотово! Результаты в {output_dir}/")


if __name__ == "__main__":
    config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../configuration/Prod")
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("../parsed_metadata")
    export(config, output)
