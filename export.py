# export_project.py
import os
import sys
from datetime import datetime
import argparse

# Папки и файлы для исключения
EXCLUDE_DIRS = {'node_modules', '__pycache__', 'tests','scripts','dist', 'build', '.git', 'venv', 'helpers', '.idea', 'logs'}
EXCLUDE_FILES = {'.DS_Store', 'package-lock.json','__init__.py','export.py','.js'}
INCLUDE_EXTENSIONS = {'.py', '.jsx', '.js', 'env','.vue'}

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

def collect_file_contents(root_dir, output_file, include_files=None):
    """Собирает содержимое файлов с указанными расширениями или конкретных файлов."""
    for root, _, files in os.walk(root_dir):
        if any(exclude in root for exclude in EXCLUDE_DIRS):
            continue
        for file in sorted(files):
            if os.path.splitext(file)[1] in INCLUDE_EXTENSIONS and file not in EXCLUDE_FILES:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, start='.')  # Относительный путь
                if include_files and relative_path not in include_files:
                    continue
                output_file.write(f"\n{'='*80}\n")
                output_file.write(f"File: {relative_path}\n")
                output_file.write(f"{'='*80}\n")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():  # Пропуск пустых файлов
                            output_file.write(content)
                            output_file.write('\n')
                        else:
                            output_file.write(f"Файл пуст\n")
                except UnicodeDecodeError:
                    output_file.write(f"Ошибка: файл {relative_path} не в UTF-8 кодировке\n")
                except Exception as e:
                    output_file.write(f"Ошибка при чтении файла {relative_path}: {e}\n")

def main():
    # Парсер аргументов для фильтрации файлов
    parser = argparse.ArgumentParser(description="Экспорт структуры и кода проекта")
    parser.add_argument('files', nargs='*', help="Список файлов для включения (относительные пути, например, backend/db/database.py)")
    args = parser.parse_args()
    include_files = set(args.files) if args.files else None

    # Формирование имени файла с временной меткой
    output_file_path = f"project_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        output_file.write(f"Project Export Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        output_file.write("\n=== Project Structure ===\n")
        output_file.write(".\n")
        get_project_structure('.', output_file)
        output_file.write("\n=== File Contents ===\n")
        collect_file_contents('.', output_file, include_files)
    
    print(f"Структура и код сохранены в {output_file_path}")

if __name__ == "__main__":
    main()