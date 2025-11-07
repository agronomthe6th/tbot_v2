import logging
from datetime import datetime
from typing import List, Dict, Optional
from telethon import TelegramClient
from telethon.tl.types import Channel, Message
import asyncio

logger = logging.getLogger(__name__)

class TelegramScraper:
    """
    Сборщик сообщений из Telegram каналов
    """
    
    def __init__(self, api_id: int, api_hash: str, db_manager, session_name: str = "trader_session"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.db = db_manager
        self.session_name = session_name
        self.client = None
        self.is_running = False
        self.channels = {}
        
    async def initialize(self):
        """
        Инициализация клиента Telethon
        
        При первом запуске:
        1. Попросит номер телефона
        2. Попросит код из Telegram сообщения
        3. Попросит 2FA пароль (облачный пароль)
        4. Сохранит сессию в файл
        
        При следующих запусках - использует сохраненную сессию
        """
        try:
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            await self.client.start()
            logger.info("✅ Telegram client initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Telegram client: {e}")
            return False
    
    async def add_channel(self, channel_id: int, name: str, enabled: bool = True):
        """
        Добавить канал для мониторинга
        
        Args:
            channel_id: ID канала в Telegram
            name: Название для логов
            enabled: Активен ли канал
        """
        try:
            entity = None
            
            # Сначала ищем в диалогах (самый надежный способ)
            async for dialog in self.client.iter_dialogs():
                if dialog.entity.id == channel_id:
                    entity = dialog.entity
                    actual_name = dialog.title
                    logger.info(f"✅ Found channel in dialogs: {actual_name}")
                    break
            
            # Если не нашли в диалогах, пробуем напрямую
            if not entity:
                logger.warning(f"Channel {channel_id} not in dialogs, trying direct access...")
                entity = await self.client.get_entity(channel_id)
                actual_name = name
            
            self.channels[channel_id] = {
                'id': channel_id,
                'name': actual_name if entity else name,
                'entity': entity,
                'enabled': enabled,
                'last_message_id': None,
                'total_collected': 0
            }
            
            logger.info(f"✅ Channel added: {actual_name if entity else name} (ID: {channel_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add channel {channel_id}: {e}")
            return False
    
    async def fetch_history(self, channel_id: int, limit: int = 100) -> int:
        """
        Загрузить историю сообщений из канала
        
        Args:
            channel_id: ID канала
            limit: Максимум сообщений
            
        Returns:
            int: Количество собранных сообщений
        """
        if channel_id not in self.channels:
            logger.error(f"❌ Channel {channel_id} not configured")
            return 0
        
        channel = self.channels[channel_id]
        if not channel['enabled']:
            logger.warning(f"⚠️ Channel {channel['name']} is disabled")
            return 0
        
        try:
            entity = channel['entity']
            collected = 0
            
            logger.info(f"📥 Fetching history from {channel['name']} (limit: {limit})...")
            
            async for message in self.client.iter_messages(entity, limit=limit):
                if await self._save_message(channel_id, message):
                    collected += 1
                    
                    if channel['last_message_id'] is None or message.id > channel['last_message_id']:
                        channel['last_message_id'] = message.id
            
            channel['total_collected'] += collected
            logger.info(f"✅ Collected {collected} messages from {channel['name']}")
            return collected
            
        except Exception as e:
            logger.error(f"❌ Error fetching history from {channel_id}: {e}")
            return 0
    
    async def fetch_new_messages(self, channel_id: int) -> int:
        """
        Загрузить только новые сообщения (после last_message_id)
        
        Args:
            channel_id: ID канала
            
        Returns:
            int: Количество новых сообщений
        """
        if channel_id not in self.channels:
            return 0
        
        channel = self.channels[channel_id]
        if not channel['enabled']:
            return 0
        
        try:
            entity = channel['entity']
            last_id = channel['last_message_id'] or 0
            collected = 0
            
            async for message in self.client.iter_messages(entity, min_id=last_id, limit=100):
                if await self._save_message(channel_id, message):
                    collected += 1
                    
                    if message.id > last_id:
                        channel['last_message_id'] = message.id
            
            if collected > 0:
                channel['total_collected'] += collected
                logger.info(f"✅ Collected {collected} new messages from {channel['name']}")
            
            return collected
            
        except Exception as e:
            logger.error(f"❌ Error fetching new messages from {channel_id}: {e}")
            return 0
    
    async def _save_message(self, channel_id: int, message: Message) -> bool:
        """
        Сохранить сообщение в БД (только текст и метаданные)
        
        Args:
            channel_id: ID канала
            message: Объект сообщения из Telethon
            
        Returns:
            bool: True если сохранено, False если дубликат или ошибка
        """
        try:
            if not message.text:
                return False
            
            # Сохраняем только основные данные
            message_id = self.db.save_message(
                channel_id=channel_id,
                message_id=message.id,
                timestamp=message.date,
                text=message.text,
                is_processed=False
            )
            
            if message_id:
                return True
            return False
            
        except Exception as e:
            if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                return False
            
            logger.error(f"❌ Error saving message {message.id}: {e}")
            return False
    
    async def start_monitoring(self, interval_seconds: int = 60):
        """
        Запустить мониторинг каналов в фоне
        
        Args:
            interval_seconds: Интервал проверки новых сообщений
        """
        self.is_running = True
        logger.info(f"🔄 Started monitoring with interval {interval_seconds}s")
        
        while self.is_running:
            try:
                for channel_id in self.channels:
                    if self.channels[channel_id]['enabled']:
                        await self.fetch_new_messages(channel_id)
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(interval_seconds)
    
    def stop_monitoring(self):
        """Остановить мониторинг"""
        self.is_running = False
        logger.info("⏸️ Monitoring stopped")
    
    def get_status(self) -> Dict:
        """Получить статус сборщика"""
        channels_status = []
        
        for ch_id, ch_data in self.channels.items():
            channels_status.append({
                'id': ch_id,
                'name': ch_data['name'],
                'enabled': ch_data['enabled'],
                'last_message_id': ch_data['last_message_id'],
                'total_collected': ch_data['total_collected']
            })
        
        return {
            'is_running': self.is_running,
            'client_connected': self.client is not None and self.client.is_connected(),
            'channels': channels_status
        }
    
    async def close(self):
        """Закрыть соединение"""
        self.stop_monitoring()
        if self.client:
            await self.client.disconnect()
            logger.info("👋 Telegram client disconnected")