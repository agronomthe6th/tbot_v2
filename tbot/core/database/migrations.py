# core/database/migrations.py
"""
Функции для создания и обновления схемы БД
"""
import logging
from sqlalchemy import MetaData
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