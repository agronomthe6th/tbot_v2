#!/usr/bin/env python3
"""
Скрипт для проверки и создания таблиц в БД
"""
import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tbot'))

from dotenv import load_dotenv
from core.database import Database
from core.database.models import Base
from sqlalchemy import text

def main():
    load_dotenv()

    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not found in .env")
        return 1

    print(f"📊 Connecting to database...")
    print(f"   URL: {db_url[:50]}...")

    try:
        db = Database(db_url)
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return 1

    # Проверяем существование таблицы telegram_channels
    try:
        with db.session() as session:
            result = session.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='telegram_channels')")
            )
            exists = result.fetchone()[0]

            if exists:
                print("✅ Table 'telegram_channels' exists")

                # Считаем записи
                result = session.execute(text("SELECT COUNT(*) FROM telegram_channels"))
                count = result.fetchone()[0]
                print(f"   Total channels: {count}")

                # Показываем каналы
                if count > 0:
                    result = session.execute(
                        text("SELECT channel_id, name, is_enabled FROM telegram_channels ORDER BY name")
                    )
                    print("\n📋 Existing channels:")
                    for row in result:
                        status = "✅" if row[2] else "⛔"
                        print(f"   {status} {row[1]} (ID: {row[0]})")
            else:
                print("⚠️  Table 'telegram_channels' does not exist")
                print("🔧 Creating table...")

                # Создаем таблицу
                Base.metadata.create_all(db.engine, tables=[Base.metadata.tables.get('telegram_channels')])
                print("✅ Table created successfully")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    print("\n✨ Database check completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
