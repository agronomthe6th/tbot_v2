#!/usr/bin/env python3
"""
Скрипт для миграции Telegram каналов из .env в базу данных.
Запустите один раз для переноса каналов из хардкода в БД.

Usage:
    python migrate_channels_to_db.py
"""

import os
import sys
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tbot.core.database.database import DatabaseManager
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

def migrate_channels():
    """Миграция каналов из .env в базу данных"""

    print("🔄 Начинаем миграцию каналов из .env в базу данных...")

    # Инициализируем подключение к БД
    db = DatabaseManager()

    channels_to_migrate = []

    # Читаем каналы из .env
    target_channel_id = os.getenv("target_channel_id")
    test_channel_id = os.getenv("test_channel_id")

    if target_channel_id:
        channels_to_migrate.append({
            "channel_id": int(target_channel_id),
            "name": "Main Trading Channel",
            "username": None,
            "is_enabled": True
        })
        print(f"✓ Найден target_channel_id: {target_channel_id}")

    if test_channel_id:
        channels_to_migrate.append({
            "channel_id": int(test_channel_id),
            "name": "Test Channel",
            "username": None,
            "is_enabled": False
        })
        print(f"✓ Найден test_channel_id: {test_channel_id}")

    if not channels_to_migrate:
        print("⚠️  Не найдено каналов в .env файле")
        print("Убедитесь что в .env есть переменные:")
        print("  - target_channel_id")
        print("  - test_channel_id")
        return

    # Мигрируем каналы
    migrated_count = 0
    for channel in channels_to_migrate:
        try:
            # Проверяем, существует ли канал
            existing = db.get_channel_by_id(channel["channel_id"])

            if existing:
                print(f"⚠️  Канал {channel['name']} (ID: {channel['channel_id']}) уже существует в БД")
                print(f"   Обновляем данные...")
                db.update_channel(
                    channel["channel_id"],
                    name=channel["name"],
                    is_enabled=channel["is_enabled"]
                )
                print(f"✅ Канал обновлен: {channel['name']}")
            else:
                # Создаем новый канал
                record_id = db.create_channel(
                    channel_id=channel["channel_id"],
                    name=channel["name"],
                    username=channel["username"],
                    is_enabled=channel["is_enabled"]
                )
                print(f"✅ Канал добавлен: {channel['name']} (ID: {channel['channel_id']}, record_id: {record_id})")

            migrated_count += 1

        except Exception as e:
            print(f"❌ Ошибка при миграции канала {channel['name']}: {e}")

    print(f"\n🎉 Миграция завершена! Обработано каналов: {migrated_count}/{len(channels_to_migrate)}")
    print("\n📝 Теперь вы можете:")
    print("   1. Удалить target_channel_id и test_channel_id из .env (необязательно)")
    print("   2. Управлять каналами через веб-интерфейс в DataManagement")
    print("   3. Добавлять новые каналы через UI без редактирования кода")

if __name__ == "__main__":
    try:
        migrate_channels()
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
