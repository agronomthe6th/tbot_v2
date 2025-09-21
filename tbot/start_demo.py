# run.py - Простой запуск существующего проекта
import os
import sys
import asyncio
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

def main():
    """Простой запуск проекта как есть"""
    print("🚀 Starting Trader Tracker...")
    
    # Загружаем .env если есть
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv()
        print("✅ Loaded .env file")
    else:
        print("⚠️  No .env file found, using defaults")
    
    # Проверяем что БД настроена
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not configured")
        print("💡 Set DATABASE_URL environment variable or create .env file")
        return
    
    print(f"📚 Database: {database_url}")
    
    # Создаем директорию для логов если нет
    os.makedirs("logs", exist_ok=True)
    
    # Запускаем существующее API приложение
    try:
        print("🌐 Starting API server...")
        print("📊 Access API at: http://localhost:8000")
        print("📋 API docs at: http://localhost:8000/docs")
        print("💡 Press Ctrl+C to stop")
        
        # Импортируем существующее приложение
        from api.app import app
        
        # Запускаем uvicorn
        uvicorn.run(
            app,
            host="0.0.0.0", 
            port=8000,
            log_level="info",
            reload=False  # Отключаем reload для стабильности
        )
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        print("💡 Check your configuration and database connection")

if __name__ == "__main__":
    # Проверяем зависимости
    try:
        import fastapi
        import sqlalchemy
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Install dependencies: pip install -r requirements.txt")
        sys.exit(1)
    
    main()