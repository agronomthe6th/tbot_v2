#!/usr/bin/env python3
"""
Скрипт для запуска миграции улучшений системы консенсусов
"""
import sys
import logging
import os
from pathlib import Path

# Добавляем путь к модулю tbot
sys.path.insert(0, str(Path(__file__).parent))

from tbot.core.database import Database
from tbot.core.database.migrations import migrate_consensus_improvements

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Запуск миграции"""
    logger.info("🚀 Starting consensus improvements migration...")

    try:
        # Получаем URL базы данных из переменных окружения
        database_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/trader_tracker")
        logger.info(f"Connecting to database...")

        # Создаем экземпляр Database
        db = Database(database_url)

        # Запускаем миграцию
        success = migrate_consensus_improvements(db.engine)

        if success:
            logger.info("✅ Migration completed successfully!")
            db.close()
            return 0
        else:
            logger.error("❌ Migration failed!")
            db.close()
            return 1

    except Exception as e:
        logger.error(f"❌ Migration error: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
