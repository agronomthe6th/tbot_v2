#!/usr/bin/env python3
"""
Скрипт для запуска миграции улучшений системы консенсусов
"""
import sys
import logging
from pathlib import Path

# Добавляем путь к модулю tbot
sys.path.insert(0, str(Path(__file__).parent))

from tbot.core.database.database import get_db_manager
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
        # Получаем экземпляр БД
        db = get_db_manager()
        engine = db.engine

        # Запускаем миграцию
        success = migrate_consensus_improvements(engine)

        if success:
            logger.info("✅ Migration completed successfully!")
            return 0
        else:
            logger.error("❌ Migration failed!")
            return 1

    except Exception as e:
        logger.error(f"❌ Migration error: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
