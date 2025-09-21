# migrate_data.py - Простой перенос raw_messages из старой БД в новую
"""
СКРИПТ МИГРАЦИИ RAW MESSAGES

НАЗНАЧЕНИЕ: 
Просто копирует raw_messages из старой БД (trading_signals:5433) в новую (trader_tracker:5432)

ЛОГИКА:
1. Подключается к старой БД на порту 5433
2. Читает все raw_messages 
3. Вставляет их в новую БД на порту 5432
4. НИКАКОЙ ОБРАБОТКИ - просто копирование!

ПАРСИНГ СИГНАЛОВ:
Делается ОТДЕЛЬНО через regex после миграции.
Этот скрипт только переносит сырые сообщения.

ИСПОЛЬЗОВАНИЕ:
python migrate_data.py [--dry-run] [--limit N]

СТРУКТУРА СТАРОЙ БД (raw_messages):
- id, timestamp, channel_id, message_id  
- author_id, author_username, author_first_name
- text, views, forwards, edit_date
- media_type, reply_to_message_id, raw_data
- collected_at, is_processed, processing_attempts
"""

import asyncio
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional
import json

import psycopg2
from psycopg2.extras import RealDictCursor
from core.database import UnifiedDatabaseManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("raw_migration")

class RawMessageMigration:
    """Простая миграция raw_messages между БД"""
    
    def __init__(self, old_db_url: str, new_db_url: str, dry_run: bool = False):
        self.old_db_url = old_db_url  
        self.new_db_url = new_db_url
        self.dry_run = dry_run
        
        # Подключения
        self.old_conn = None
        self.new_db_manager = None
        
        # Статистика
        self.stats = {
            'total_found': 0,
            'migrated': 0,
            'skipped': 0,
            'errors': 0
        }
    
    async def run_migration(self, limit: Optional[int] = None):
        """Основная функция миграции"""
        logger.info("🚀 Начинаем перенос raw_messages...")
        logger.info(f"Режим: {'DRY RUN' if self.dry_run else 'РЕАЛЬНЫЙ ПЕРЕНОС'}")
        
        try:
            # 1. Подключения к БД
            await self._connect_databases()
            
            # 2. Загрузка raw_messages из старой БД
            old_messages = await self._load_old_raw_messages(limit)
            self.stats['total_found'] = len(old_messages)
            logger.info(f"📊 Найдено {len(old_messages)} raw_messages")
            
            # 3. Перенос в новую БД
            await self._migrate_raw_messages(old_messages)
            
            # 4. Статистика
            self._print_stats()
            
        except Exception as e:
            logger.error(f"❌ Ошибка миграции: {e}")
            raise
        finally:
            await self._disconnect()
        
        logger.info("✅ Миграция raw_messages завершена!")
    
    async def _connect_databases(self):
        """Подключение к старой и новой БД"""
        logger.info("🔌 Подключаемся к базам данных...")
        
        # Старая БД
        try:
            self.old_conn = psycopg2.connect(self.old_db_url)
            self.old_conn.set_client_encoding('UTF8')
            logger.info("✅ Старая БД подключена")
        except Exception as e:
            logger.error(f"❌ Старая БД: {e}")
            raise
        
        # Новая БД
        try:
            self.new_db_manager = UnifiedDatabaseManager(self.new_db_url)
            if not self.new_db_manager.initialize():
                raise Exception("Не удалось инициализировать новую БД")
            logger.info("✅ Новая БД подключена")
        except Exception as e:
            logger.error(f"❌ Новая БД: {e}")
            raise
    
    async def _load_old_raw_messages(self, limit: Optional[int] = None) -> List[Dict]:
        """Загрузка raw_messages из старой БД"""
        logger.info("📥 Загружаем raw_messages из старой БД...")
        
        # Простой SELECT * без обработки
        query = """
            SELECT 
                id, timestamp, channel_id, message_id,
                author_id, author_username, author_first_name,
                text, views, forwards, edit_date,
                media_type, reply_to_message_id, raw_data,
                collected_at, is_processed, processing_attempts
            FROM raw_messages 
            ORDER BY timestamp ASC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        with self.old_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            messages = cursor.fetchall()
        
        return [dict(msg) for msg in messages]
    
    async def _migrate_raw_messages(self, old_messages: List[Dict]):
        """Перенос raw_messages в новую БД"""
        logger.info(f"🔄 Переносим {len(old_messages)} сообщений...")
        
        for i, old_msg in enumerate(old_messages, 1):
            try:
                success = await self._insert_single_message(old_msg)
                
                if success:
                    self.stats['migrated'] += 1
                else:
                    self.stats['skipped'] += 1
                
                # Прогресс каждые 100 сообщений
                if i % 100 == 0:
                    logger.info(f"📈 Обработано {i}/{len(old_messages)} сообщений")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка с сообщением {old_msg.get('id', '?')}: {e}")
                self.stats['errors'] += 1
                continue
    
    async def _insert_single_message(self, old_msg: Dict) -> bool:
        """Вставка одного сообщения в новую БД"""
        
        if self.dry_run:
            # В тестовом режиме только логируем
            logger.debug(f"DRY RUN: сообщение {old_msg['id']} от {old_msg['timestamp']}")
            return True
        
        # Подготавливаем данные для новой БД
        # НЕ ПАРСИМ - просто копируем как есть!
        new_msg_data = {
            # Временные метки
            'timestamp': old_msg['timestamp'],
            'collected_at': old_msg['collected_at'],
            
            # Идентификаторы
            'channel_id': old_msg['channel_id'],
            'message_id': old_msg['message_id'],
            
            # Автор
            'author_id': old_msg['author_id'],
            'author_username': old_msg['author_username'],
            'author_first_name': old_msg['author_first_name'],
            
            # Содержимое
            'text': old_msg['text'] or '',
            'views': old_msg['views'] or 0,
            'forwards': old_msg['forwards'] or 0,
            'edit_date': old_msg['edit_date'],
            
            # Метаданные
            'media_type': old_msg['media_type'],
            'reply_to_message_id': old_msg['reply_to_message_id'],
            'raw_data': old_msg['raw_data'],  # JSON как есть
            
            # Статус обработки
            'is_processed': old_msg['is_processed'] or False,
            'processing_attempts': old_msg['processing_attempts'] or 0
        }
        
        # Вставляем через менеджер БД
        message_id = self.new_db_manager.save_raw_message(**new_msg_data)
        
        return message_id is not None
    
    def _print_stats(self):
        """Вывод статистики миграции"""
        logger.info("\n" + "="*50)
        logger.info("📊 СТАТИСТИКА МИГРАЦИИ")
        logger.info("="*50)
        logger.info(f"Найдено в старой БД: {self.stats['total_found']}")
        logger.info(f"Успешно перенесено: {self.stats['migrated']}")
        logger.info(f"Пропущено: {self.stats['skipped']}")
        logger.info(f"Ошибок: {self.stats['errors']}")
        logger.info("="*50)
        
        if self.stats['total_found'] > 0:
            success_rate = (self.stats['migrated'] / self.stats['total_found']) * 100
            logger.info(f"Успешность: {success_rate:.1f}%")
    
    async def _disconnect(self):
        """Закрытие подключений"""
        if self.old_conn:
            self.old_conn.close()
        logger.info("🔌 Подключения закрыты")


# CLI интерфейс
async def main():
    parser = argparse.ArgumentParser(description="Миграция raw_messages между БД")
    parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Тестовый запуск без изменений в БД'
    )
    parser.add_argument(
        '--limit', 
        type=int, 
        help='Ограничение количества сообщений для миграции'
    )
    parser.add_argument(
        '--old-db',
        default='postgresql://postgres:password@localhost:5433/trading_signals',
        help='URL старой БД'
    )
    parser.add_argument(
        '--new-db', 
        default='postgresql://postgres:password@localhost:5432/trader_tracker',
        help='URL новой БД'
    )
    
    args = parser.parse_args()
    
    # Запуск миграции
    migration = RawMessageMigration(
        old_db_url=args.old_db,
        new_db_url=args.new_db,
        dry_run=args.dry_run
    )
    
    await migration.run_migration(limit=args.limit)


if __name__ == "__main__":
    print("""
    МИГРАЦИЯ RAW MESSAGES
    =====================
    
    Этот скрипт просто копирует raw_messages из старой БД в новую.
    НИКАКОЙ ОБРАБОТКИ - только перенос данных как есть!
    
    Парсинг сигналов будет делаться отдельно через regex.
    
    Примеры использования:
    
    # Тестовый запуск
    python migrate_data.py --dry-run --limit 10
    
    # Реальная миграция всех сообщений  
    python migrate_data.py
    
    # Миграция с ограничением
    python migrate_data.py --limit 1000
    
    """)
    
    asyncio.run(main())