# core/database/migrations.py
"""
Функции для создания и обновления схемы БД
"""
import logging
from sqlalchemy import MetaData, text
from .models import Base

logger = logging.getLogger(__name__)

def create_tables(engine):
    """
    Создать все таблицы в БД
    
    Args:
        engine: SQLAlchemy engine
    """
    try:
        Base.metadata.create_all(engine)
        logger.info("✅ All database tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        return False

def drop_tables(engine):
    """
    Удалить все таблицы из БД (ОСТОРОЖНО!)
    
    Args:
        engine: SQLAlchemy engine
    """
    try:
        Base.metadata.drop_all(engine)
        logger.warning("⚠️ All database tables dropped")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to drop tables: {e}")
        return False

def get_table_info(engine) -> dict:
    """
    Получить информацию о существующих таблицах
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        dict: информация о таблицах
    """
    try:
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        tables_info = {}
        for table_name, table in metadata.tables.items():
            tables_info[table_name] = {
                'columns': len(table.columns),
                'indexes': len(table.indexes),
                'foreign_keys': len([fk for col in table.columns for fk in col.foreign_keys])
            }
        
        return tables_info
        
    except Exception as e:
        logger.error(f"❌ Failed to get table info: {e}")
        return {}

def migrate_consensus_improvements(engine):
    """
    Миграция для улучшений системы консенсусов:
    - Добавление поля indicator_conditions в consensus_rules
    - Создание таблицы consensus_backtests

    Args:
        engine: SQLAlchemy engine
    """
    try:
        with engine.connect() as conn:
            # Проверяем существует ли колонка indicator_conditions
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'consensus_rules'
                AND column_name = 'indicator_conditions'
            """))

            if not result.fetchone():
                logger.info("Adding indicator_conditions column to consensus_rules...")
                conn.execute(text("""
                    ALTER TABLE consensus_rules
                    ADD COLUMN indicator_conditions JSONB
                """))
                conn.commit()
                logger.info("✅ Added indicator_conditions column")
            else:
                logger.info("Column indicator_conditions already exists")

            # Проверяем существует ли таблица consensus_backtests
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = 'consensus_backtests'
            """))

            if not result.fetchone():
                logger.info("Creating consensus_backtests table...")
                # Используем create_all для создания новой таблицы
                Base.metadata.create_all(engine, tables=[Base.metadata.tables['consensus_backtests']])
                logger.info("✅ Created consensus_backtests table")
            else:
                logger.info("Table consensus_backtests already exists")

        logger.info("✅ Consensus improvements migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return False