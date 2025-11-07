#!/usr/bin/env python3
import os
import argparse
from datetime import datetime

# Папки и файлы для исключения
EXCLUDE_DIRS = {
    'node_modules', '__pycache__', 'tests', 'scripts',
    'dist', 'build', '.git', 'venv', 'helpers', '.idea', 'logs', 'codebase_export'
}
EXCLUDE_FILES = {'.DS_Store', 'package-lock.json', '__init__.py', 'export.py'}
INCLUDE_EXTENSIONS = {'.py', '.jsx', '.env', '.vue','.php'}

EXPORT_DIR = 'codebase_export'

# ---------------------------
# Получение структуры проекта
# ---------------------------
def get_project_structure(root_dir, output_file, prefix='', level=0):
    """Выводит структуру проекта в виде дерева и записывает в файл."""
    try:
        items = sorted(os.listdir(root_dir))
        for index, item in enumerate(items):
            path = os.path.join(root_dir, item)
            is_last = index == len(items) - 1
            tree_char = '└── ' if is_last else '├── '
            relative_path = os.path.relpath(path, start='.')

            if os.path.isdir(path) and item not in EXCLUDE_DIRS:
                output_file.write(f"{prefix}{tree_char}{item}\n")
                new_prefix = prefix + ('    ' if is_last else '│   ')
                get_project_structure(path, output_file, new_prefix, level + 1)
            elif os.path.isfile(path) and os.path.splitext(item)[1] in INCLUDE_EXTENSIONS and item not in EXCLUDE_FILES:
                output_file.write(f"{prefix}{tree_char}{relative_path}\n")
    except Exception as e:
        output_file.write(f"{prefix}Ошибка при сканировании директории {root_dir}: {e}\n")

# ---------------------------
# Сбор содержимого всех файлов
# ---------------------------
def collect_file_contents(root_dir, include_files=None):
    contents = []
    for root, _, files in os.walk(root_dir):
        if any(ex in root for ex in EXCLUDE_DIRS):
            continue
        for file in sorted(files):
            if os.path.splitext(file)[1] in INCLUDE_EXTENSIONS and file not in EXCLUDE_FILES:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, start='.')

                if include_files and relative_path not in include_files:
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if not lines:
                            lines = ["Файл пуст\n"]

                        formatted = [
                            "\n" + "=" * 80 + "\n",
                            f"File: {relative_path}\n",
                            "=" * 80 + "\n"
                        ] + lines + ["\n"]
                        contents.extend(formatted)
                except UnicodeDecodeError:
                    contents.append(f"Ошибка: файл {relative_path} не в UTF-8 кодировке\n")
                except Exception as e:
                    contents.append(f"Ошибка при чтении файла {relative_path}: {e}\n")
    return contents

# ---------------------------
# Разделение по строкам
# ---------------------------
def split_lines(lines, num_parts=10):
    """Разделяет кодовую базу по строкам, стараясь не рвать функции."""
    total_lines = len(lines)
    target_lines = total_lines // num_parts
    parts = []
    current = []

    count = 0
    for i, line in enumerate(lines):
        current.append(line)
        count += 1
        # если мы достигли лимита и следующая строка выглядит как начало функции/класса
        if count >= target_lines and i < len(lines) - 1:
            next_line = lines[i + 1].lstrip()
            if next_line.startswith(('def ', 'class ', '#')) or len(current) > target_lines * 1.2:
                current.append("\n=== КОД ОБРЫВАЕТСЯ. ПРОДОЛЖЕНИЕ В СЛЕДУЮЩЕМ ФАЙЛЕ ===\n\n")
                parts.append(current)
                current = ["\n=== ПРОДОЛЖЕНИЕ С ПРЕДЫДУЩЕГО ФАЙЛА ===\n\n"]
                count = 0
    if current:
        parts.append(current)
    return parts

# ---------------------------
# Основная функция
# ---------------------------
def main():
    parser = argparse.ArgumentParser(description="Экспорт структуры и кода проекта с равномерным делением по строкам")
    parser.add_argument('files', nargs='*', help="Список файлов для включения (относительные пути)")
    args = parser.parse_args()

    include_files = set(args.files) if args.files else None
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    os.makedirs(EXPORT_DIR, exist_ok=True)

    # 1. Структура проекта
    structure_file = os.path.join(EXPORT_DIR, f"project_structure_{timestamp}.txt")
    with open(structure_file, 'w', encoding='utf-8') as sf:
        sf.write("=== Project Structure ===\n.\n")
        get_project_structure('.', sf)
    print(f"Структура сохранена в {structure_file}")

    # 2. Сбор строк
    all_lines = collect_file_contents('.', include_files)

    # 3. Разделение по строкам
    parts = split_lines(all_lines, num_parts=10)

    # 4. Сохранение частей
    for i, part in enumerate(parts, start=1):
        part_file = os.path.join(EXPORT_DIR, f"project_export_part_{i}_{timestamp}.txt")
        with open(part_file, 'w', encoding='utf-8') as pf:
            pf.write(f"=== EXPORT PART {i}/{len(parts)} ===\n")
            pf.write("".join(part))
        print(f"Часть {i} сохранена в {part_file}")

    print(f"Экспорт завершён! Всего частей: {len(parts)}")

if __name__ == "__main__":
    main()
