# export_project_split.py
import os
import argparse
from datetime import datetime

# Папки и файлы для исключения
EXCLUDE_DIRS = {'node_modules', '__pycache__', 'tests', 'scripts', 'dist', 'build', '.git', 'venv', 'helpers', '.idea', 'logs'}
EXCLUDE_FILES = {'.DS_Store', 'package-lock.json', '__init__.py', 'export.py', '.js'}
INCLUDE_EXTENSIONS = {'.py', '.jsx', '.js', '.env', '.vue'}

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
            relative_path = os.path.relpath(path, start='.')  # Относительный путь

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
    """Собирает содержимое файлов и возвращает список (file_header + file_content)."""
    contents = []
    for root, _, files in os.walk(root_dir):
        if any(exclude in root for exclude in EXCLUDE_DIRS):
            continue
        for file in sorted(files):
            if os.path.splitext(file)[1] in INCLUDE_EXTENSIONS and file not in EXCLUDE_FILES:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, start='.')

                if include_files and relative_path not in include_files:
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if not content.strip():
                            content = "Файл пуст\n"

                        # Добавляем форматированный кусок
                        formatted = (
                            "\n" + "=" * 80 + "\n" +
                            f"File: {relative_path}\n" +
                            "=" * 80 + "\n" +
                            content + "\n"
                        )
                        contents.append(formatted)
                except UnicodeDecodeError:
                    contents.append(f"Ошибка: файл {relative_path} не в UTF-8 кодировке\n")
                except Exception as e:
                    contents.append(f"Ошибка при чтении файла {relative_path}: {e}\n")
    return contents

# ---------------------------
# Разделение на части
# ---------------------------
def split_into_parts(all_contents, num_parts=10):
    """Разделяет список текстов на num_parts примерно одинакового размера."""
    total_length = sum(len(item) for item in all_contents)
    target_size = total_length // num_parts + 1

    parts = [[] for _ in range(num_parts)]
    current_part = 0
    current_size = 0

    for content in all_contents:
        content_size = len(content)
        if current_size + content_size > target_size and current_part < num_parts - 1:
            current_part += 1
            current_size = 0
        parts[current_part].append(content)
        current_size += content_size

    return parts

# ---------------------------
# Основная функция
# ---------------------------
def main():
    parser = argparse.ArgumentParser(description="Экспорт структуры и кода проекта с разбиением на файлы")
    parser.add_argument('files', nargs='*', help="Список файлов для включения (относительные пути)")
    args = parser.parse_args()

    include_files = set(args.files) if args.files else None
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 1. Сохраняем структуру проекта
    structure_file = f"project_structure_{timestamp}.txt"
    with open(structure_file, 'w', encoding='utf-8') as sf:
        sf.write("=== Project Structure ===\n.\n")
        get_project_structure('.', sf)
    print(f"Структура сохранена в {structure_file}")

    # 2. Собираем содержимое всех файлов
    all_contents = collect_file_contents('.', include_files)

    # 3. Разделяем на ~10 частей
    parts = split_into_parts(all_contents, num_parts=10)

    # 4. Сохраняем каждую часть в отдельный файл
    for i, part in enumerate(parts, start=1):
        part_file = f"project_export_part_{i}_{timestamp}.txt"
        with open(part_file, 'w', encoding='utf-8') as pf:
            pf.write("".join(part))
        print(f"Часть {i} сохранена в {part_file}")

    print("Экспорт завершён!")

if __name__ == "__main__":
    main()
