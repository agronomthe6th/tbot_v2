# debug_tinkoff.py - Скрипт для диагностики проблем с Tinkoff токеном
import os
import asyncio
from dotenv import load_dotenv

async def debug_tinkoff_token():
    """Полная диагностика проблем с Tinkoff токеном"""
    
    print("🔍 ДИАГНОСТИКА TINKOFF TOKEN")
    print("=" * 50)
    
    # 1. Проверка загрузки .env файла
    load_dotenv()
    print("✅ .env файл загружен")
    
    # 2. Проверка токена
    token = os.getenv("TINKOFF_TOKEN")
    sandbox = os.getenv("TINKOFF_SANDBOX")
    
    print(f"📋 TOKEN присутствует: {token is not None}")
    print(f"📋 TOKEN длина: {len(token) if token else 0}")
    print(f"📋 TOKEN первые 10 символов: {token[:10] if token else 'НЕТ'}")
    print(f"📋 TOKEN последние 10 символов: {token[-10:] if token else 'НЕТ'}")
    print(f"📋 SANDBOX режим: {sandbox}")
    
    # 3. Проверка скрытых символов в токене
    if token:

        
        # Очистка токена от возможных скрытых символов
        clean_token = token.strip().replace('\n', '').replace('\r', '')
        print(f"📋 TOKEN после очистки длина: {len(clean_token)}")
        print(f"📋 Токен изменился после очистки: {token != clean_token}")
    
    # 4. Проверка библиотеки tinkoff-invest
    try:
        from tinkoff.invest import AsyncClient
        print("✅ Библиотека tinkoff-invest импортирована")
        
        # Проверяем версию если возможно
        try:
            import tinkoff.invest
            print(f"📦 Версия tinkoff-invest: {getattr(tinkoff.invest, '__version__', 'НЕИЗВЕСТНО')}")
        except:
            print("⚠️ Не удалось определить версию tinkoff-invest")
            
    except ImportError as e:
        print(f"❌ Ошибка импорта tinkoff-invest: {e}")
        return
    
    # 5. Тест прямого подключения (старый способ)
    if token:
        print("\n🧪 ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ...")
        clean_token = token.strip()
        
        try:
            async with AsyncClient(clean_token) as client:
                print("✅ AsyncClient создан успешно")
                
                # Попробуем получить аккаунты
                accounts = await client.users.get_accounts()
                print(f"✅ Получены аккаунты: {len(accounts.accounts)}")
                
                for i, account in enumerate(accounts.accounts):
                    print(f"   Аккаунт {i+1}: {account.name} ({account.type})")
                    
        except Exception as e:
            print(f"❌ Ошибка при тестировании: {e}")
            print(f"📋 Тип ошибки: {type(e).__name__}")
            
            # Дополнительная диагностика
            error_str = str(e)
            if "UNAUTHENTICATED" in error_str:
                print("🔍 Это ошибка аутентификации!")
                if "40003" in error_str:
                    print("🔍 Код ошибки 40003 - токен недействителен или отсутствует")
            
    # 6. Тест с различными вариантами токена
    if token:
        print("\n🧪 ТЕСТИРОВАНИЕ РАЗЛИЧНЫХ ВАРИАНТОВ ТОКЕНА...")
        
        test_tokens = [
            ("Исходный токен", token),
            ("Очищенный токен", token.strip()),
            ("Токен без \\n и \\r", token.replace('\n', '').replace('\r', '')),
        ]
        
        for name, test_token in test_tokens:
            if test_token != token:  # Тестируем только если отличается
                print(f"\n🔬 Тестируем: {name}")
                try:
                    async with AsyncClient(test_token) as client:
                        accounts = await client.users.get_accounts()
                        print(f"✅ {name} - РАБОТАЕТ! Аккаунтов: {len(accounts.accounts)}")
                        return test_token  # Возвращаем рабочий токен
                except Exception as e:
                    print(f"❌ {name} - НЕ РАБОТАЕТ: {str(e)[:100]}")
    
    # 7. Проверка через curl (если возможно)
    print("\n🌐 РЕКОМЕНДАЦИИ ДЛЯ РУЧНОЙ ПРОВЕРКИ:")
    if token:
        clean_token = token.strip()
        print("Попробуйте выполнить в терминале:")
        print(f'curl -H "Authorization: Bearer {clean_token}" \\')
        print('     -H "Content-Type: application/json" \\')
        print('     "https://invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.UsersService/GetAccounts"')
    
    print("\n🔧 ВОЗМОЖНЫЕ РЕШЕНИЯ:")
    print("1. Проверьте токен в Tinkoff API Console")
    print("2. Создайте новый токен")
    print("3. Убедитесь что токен для правильного режима (sandbox/production)")
    print("4. Проверьте срок действия токена")

if __name__ == "__main__":
    asyncio.run(debug_tinkoff_token())