# setup_demo.py - Скрипт для инициализации демо-версии
import asyncio
import logging
from typing import List
from datetime import datetime, timedelta

from config import config
from core.database import init_database
from integrations.tinkoff_integration import TinkoffIntegration, sync_instruments_from_tinkoff
from analysis.signal_matcher import SignalMatcher

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("setup_demo")

class DemoSetup:
    """Класс для настройки демо-версии"""
    
    def __init__(self):
        self.db_manager = None
        self.tinkoff_client = None
        self.signal_matcher = None
    
    async def run_full_setup(self):
        """Полная настройка демо-версии"""
        logger.info("🚀 Starting demo setup...")
        
        try:
            # 1. Инициализация базы данных
            await self.setup_database()
            
            # 2. Настройка Tinkoff интеграции
            if config.enable_tinkoff:
                await self.setup_tinkoff()
            
            # 3. Создание тестовых данных
            await self.create_sample_data()
            
            # 4. Настройка отслеживания сигналов
            await self.setup_signal_tracking()
            
            logger.info("✅ Demo setup completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Demo setup failed: {e}")
            raise
    
    async def setup_database():
        """Настройка базы данных"""
        print("🗄️ NOT YET IMPLEMENTED ADD DOCKER COMMAND - 'zver@pop-os:~/Documents/stuff/tbot2/tbot$ sudo docker run -d   --name timescaledb_trader_tracker   -p 5432:5432   -e POSTGRES_PASSWORD=password   -e POSTGRES_DB=trader_tracker  timescale/timescaledb:latest-pg15'")
        
        return True
        
    async def setup_tinkoff(self):
        """Настройка Tinkoff интеграции"""
        logger.info("📈 Setting up Tinkoff integration...")
        
        try:
            if not config.tinkoff.token:
                logger.warning("⚠️ Tinkoff token not configured, skipping...")
                return
            
            self.tinkoff_client = TinkoffIntegration(config.tinkoff.token)
            success = await self.tinkoff_client.initialize()
            
            if success:
                logger.info("✅ Tinkoff client initialized")
                
                # Синхронизируем основные инструменты
                await self.sync_popular_instruments()
                
            else:
                logger.error("❌ Tinkoff initialization failed")
                
        except Exception as e:
            logger.error(f"❌ Tinkoff setup failed: {e}")
            raise
    
    async def sync_popular_instruments(self):
        """Синхронизация популярных инструментов"""
        logger.info("🔄 Syncing popular instruments...")
        
        popular_tickers = [
            "SBER", "GAZP", "LKOH", "GMKN", "NVTK", 
            "YNDX", "PLZL", "MGNT", "ROSN", "TATN"
        ]
        
        synced = 0
        for ticker in popular_tickers:
            try:
                instrument = await self.tinkoff_client.find_instrument_by_ticker(ticker)
                if instrument:
                    synced += 1
                    logger.info(f"✓ Synced {ticker}")
                else:
                    logger.warning(f"✗ Failed to find {ticker}")
                    
            except Exception as e:
                logger.error(f"Error syncing {ticker}: {e}")
        
        logger.info(f"📊 Synced {synced}/{len(popular_tickers)} instruments")
    
    async def create_sample_data(self):
        """Создание образцов данных для демо"""
        logger.info("🎭 Creating sample data...")
        
        try:
            # Создаем тестовый канал
            sample_channel = {
                'id': -1001234567890,
                'name': 'Demo Trading Channel',
                'username': 'demo_trading',
                'is_active': True
            }
            
            with self.db_manager.session_scope() as session:
                from core.models import Channel
                channel = Channel(**sample_channel)
                session.merge(channel)
            
            # Создаем тестовых трейдеров
            sample_traders = [
                "DemoTrader1", "SignalMaster", "TechAnalyst", 
                "MarketGuru", "StockPicker"
            ]
            
            for trader_name in sample_traders:
                with self.db_manager.session_scope() as session:
                    from core.models import Trader
                    trader = Trader(
                        name=trader_name,
                        channel_id=sample_channel['id'],
                        is_active=True,
                        first_signal_at=datetime.now() - timedelta(days=30)
                    )
                    session.merge(trader)
            
            logger.info(f"✅ Created sample data: 1 channel, {len(sample_traders)} traders")
            
        except Exception as e:
            logger.error(f"❌ Sample data creation failed: {e}")
            raise
    
    async def setup_signal_tracking(self):
        """Настройка отслеживания сигналов"""
        logger.info("🎯 Setting up signal tracking...")
        
        try:
            self.signal_matcher = SignalMatcher(self.db_manager, self.tinkoff_client)
            
            # Обрабатываем существующие сигналы
            if self.tinkoff_client:
                processed = await self.signal_matcher.process_untracked_signals(limit=10)
                logger.info(f"📊 Processed {processed} existing signals")
            
            logger.info("✅ Signal tracking setup completed")
            
        except Exception as e:
            logger.error(f"❌ Signal tracking setup failed: {e}")
            raise
    
    async def run_health_check(self):
        """Проверка здоровья системы"""
        logger.info("🏥 Running health check...")
        
        try:
            # Проверка БД
            stats = self.db_manager.get_statistics()
            logger.info(f"📊 DB Stats: {stats}")
            
            # Проверка Tinkoff
            if self.tinkoff_client:
                test_price = await self.tinkoff_client.get_current_price("SBER")
                if test_price:
                    logger.info(f"📈 Tinkoff OK: SBER = {test_price['price']}")
                else:
                    logger.warning("⚠️ Tinkoff price fetch failed")
            
            # Проверка трейдеров
            traders = self.db_manager.get_all_traders_stats()
            logger.info(f"👥 Active traders: {len(traders)}")
            
            logger.info("✅ Health check completed")
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            raise

# Утилиты для запуска

async def main():
    """Основная функция настройки"""
    setup = DemoSetup()
    await setup.run_full_setup()
    await setup.run_health_check()

def run_setup():
    """Синхронный запуск настройки"""
    asyncio.run(main())

if __name__ == "__main__":
    run_setup()