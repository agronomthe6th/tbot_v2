# Алгоритм работы системы TBOT_V2

## От сообщения в Telegram до итогового сигнала

---

## 📋 ОБЩИЙ ОБЗОР

Система автоматически собирает торговые сигналы из Telegram-каналов, анализирует их на наличие консенсусов (согласованных мнений нескольких трейдеров), проверяет технические индикаторы и создает торговые рекомендации.

---

## 🔄 ПОЛНЫЙ ЖИЗНЕННЫЙ ЦИКЛ СИГНАЛА

### ФАЗА 1: Сбор данных из Telegram

```
┌─────────────────────────────────────────────────────────┐
│ 1. TELEGRAM SCRAPER                                     │
│    tbot/integrations/telegram_scraper.py                │
└─────────────────────────────────────────────────────────┘
```

**Что происходит:**
1. Telegram клиент подключается к мониторируемым каналам
2. Получает новые сообщения в реальном времени
3. Извлекает метаданные: автор, время, текст, ID канала

**Входные данные:**
- Список каналов из таблицы `telegram_channels`
- API credentials (api_id, api_hash)

**Выходные данные:**
- Запись в таблицу `raw_messages`:
  ```
  - id, timestamp, channel_id, message_id
  - author_id, author_username, author_first_name
  - text, views, forwards
  - is_processed = FALSE
  ```

**Критические точки:**
- ✅ Дедупликация по (channel_id, message_id)
- ✅ Обработка эмодзи и Unicode
- ⚠️ Лимиты Telegram API (запросы в минуту)

---

### ФАЗА 2: Парсинг торговых сигналов

```
┌─────────────────────────────────────────────────────────┐
│ 2. MESSAGE PARSER                                       │
│    tbot/analysis/message_parser.py                      │
└─────────────────────────────────────────────────────────┘
```

**Что происходит:**
1. `MessageParsingService` забирает необработанные сообщения (`is_processed = FALSE`)
2. `MessageParser` анализирует текст с помощью регулярных выражений из БД
3. Извлекает торговые данные: тикер, направление, цены, автора

**Алгоритм парсинга:**

```python
def parse_raw_message(message) -> ParseResult:
    1. Проверить, является ли сообщение торговым
       - Ищем ключевые слова: "покупка", "продажа", "long", "short"
       - Ищем тикеры: $SBER, #GAZP, YNDX
       - Ищем торговые эмодзи: 🔥, 📈, 📉

    2. Извлечь тикер
       - Паттерны: (?:[\$#]|тикер:?\s*)([A-Z]{3,6})
       - Валидация: 3-6 букв, не стоп-слова (VIP, BOT и т.д.)

    3. Определить направление
       - Паттерны для LONG: "покупка", "купить", "лонг"
       - Паттерны для SHORT: "продажа", "продать", "шорт"
       - Паттерны для EXIT: "закрыть", "выход"

    4. Извлечь цены
       - target_price: "цель", "таргет", "@"
       - stop_loss: "стоп", "sl"
       - take_profit: "профит", "tp"

    5. Извлечь автора
       - Ищем имя в начале сообщения
       - Fallback на author_username из метаданных

    6. Рассчитать confidence score (0.0 - 1.0)
       - +0.4 если нашли тикер
       - +0.3 если нашли направление
       - +0.2 если нашли операцию
       - +0.05 если текст длинный
       - +0.05 если есть торговые ключевые слова

    7. Вернуть ParseResult
```

**Выходные данные:**
- Запись в таблицу `parsed_signals`:
  ```
  - id (UUID)
  - ticker, direction, signal_type
  - target_price, stop_loss, take_profit
  - author, confidence_score
  - timestamp, original_text
  ```
- Обновление `raw_messages.is_processed = TRUE`

**Критические точки:**
- ✅ Извлечение автора ДО очистки текста
- ✅ Обработка различных форматов дат и цен
- ⚠️ Низкий confidence score (<0.5) = возможная ошибка

---

### ФАЗА 3: Детекция консенсуса

```
┌─────────────────────────────────────────────────────────┐
│ 3. CONSENSUS DETECTOR                                   │
│    tbot/analysis/consensus_detector.py                  │
└─────────────────────────────────────────────────────────┘
```

**Что происходит:**
1. При появлении нового сигнала (event-driven)
2. Проверяется наличие других сигналов в окне времени
3. Если найден консенсус → создается событие

**Алгоритм детекции:**

```python
def check_new_signal_sync(signal_id) -> Optional[Dict]:
    1. Загрузить активные правила консенсуса из БД
       ORDER BY priority DESC

    2. Для каждого правила:
        # Фильтры
        if rule.ticker_filter:
            if signal.ticker not in rule.tickers:
                continue  # Пропускаем это правило

        if rule.direction_filter:
            if signal.direction != rule.direction_filter:
                continue

        # Поиск консенсуса в окне
        window_start = signal.timestamp - window_minutes / 2
        window_end = signal.timestamp + window_minutes / 2

        window_signals = SELECT * FROM parsed_signals WHERE:
            - ticker = signal.ticker
            - signal_type = 'entry'
            - timestamp BETWEEN window_start AND window_end
            - direction IS NOT NULL

        # Проверка минимального количества трейдеров
        unique_authors = COUNT(DISTINCT author FROM window_signals)
        if unique_authors < rule.min_traders:
            continue

        # Проверка согласованности направления
        if rule.strict_consensus:
            if EXISTS (different directions):
                continue  # Отклоняем при разногласиях

        # Проверка технических индикаторов (если заданы)
        if rule.indicator_conditions:
            candles = GET last 100 candles for ticker
            if len(candles) < 30:
                return FALSE  # ⚠️ БАГ #5 ИСПРАВЛЕН

            indicators = TechnicalIndicators.calculate_all(candles)

            for indicator in rule.indicator_conditions:
                if indicator == 'rsi':
                    if NOT (min_rsi <= current_rsi <= max_rsi):
                        continue

                if indicator == 'macd':
                    if signal != expected_signal:
                        continue

                # То же для bollinger, obv...

        # КОНСЕНСУС НАЙДЕН!
        3. Создать ConsensusEvent:
            - ticker, direction, traders_count
            - window_minutes, first_signal_at, last_signal_at
            - avg_entry_price (среднее из всех сигналов)
            - price_spread_pct (разброс цен)
            - consensus_strength (0-100)

        4. Создать связи ConsensusSignal:
            FOR each signal in consensus:
                INSERT INTO consensus_signals (consensus_id, signal_id)

        5. Вернуть информацию о консенсусе

    return None  # Консенсус не найден
```

**Расчет силы консенсуса (0-100):**

```python
def _calculate_strength(consensus_data) -> int:
    strength = 50  # Базовое значение

    # Фактор 1: Количество трейдеров
    if traders_count >= 5: strength += 20
    elif traders_count >= 4: strength += 10

    # Фактор 2: Разброс цен (меньше = лучше)
    if price_spread < 1%: strength += 15
    elif price_spread < 2%: strength += 5
    elif price_spread > 5%: strength -= 10

    # Фактор 3: Временная кучность
    time_span = last_signal_time - first_signal_time
    if time_span < 10 min: strength += 15
    elif time_span < 20 min: strength += 5

    return min(100, max(0, strength))
```

**Выходные данные:**
- Запись в `consensus_events`:
  ```
  - id (UUID), rule_id, ticker, direction
  - traders_count, window_minutes
  - first_signal_at, last_signal_at
  - avg_entry_price, price_spread_pct
  - consensus_strength, status='active'
  ```
- Записи в `consensus_signals` (связь N:M)

**Критические точки:**
- ✅ Event-driven: проверяется при каждом новом сигнале
- ✅ Правила проверяются по приоритету (первое совпадение)
- ✅ Технические индикаторы требуют минимум 30 свечей
- ⚠️ ФИКSирован БАГ: False positive при нехватке данных

---

### ФАЗА 4: Получение рыночных данных

```
┌─────────────────────────────────────────────────────────┐
│ 4. TINKOFF INTEGRATION                                  │
│    tbot/integrations/tinkoff_integration.py             │
└─────────────────────────────────────────────────────────┘
```

**Что происходит:**
1. Система получает реальные рыночные данные через Tinkoff API
2. Валидирует и сохраняет свечи в БД
3. Предоставляет данные для технических индикаторов

**API методы:**

```python
# 1. Поиск инструмента
instrument = find_instrument_by_ticker("SBER")
→ {figi, ticker, name, type, currency, lot}

# 2. Текущая цена (с retry + rate limiting)
@async_retry(max_attempts=3, timeout=30)
async def get_current_price(ticker):
    await rate_limiter.acquire()  # ⚠️ Max 100 req/min
    response = await client.market_data.get_last_prices([figi])
    return {price, timestamp, source}

# 3. Исторические свечи
@async_retry(max_attempts=3, timeout=60)
async def get_candles(figi, interval, from_time, to_time):
    await rate_limiter.acquire()
    candles = client.get_all_candles(...)

    # Валидация и дедупликация
    validated = _validate_and_deduplicate_candles(candles)
    return validated
```

**Валидация свечей:**

```python
def _validate_and_deduplicate_candles(candles):
    valid_candles = []
    seen_times = set()

    for candle in candles:
        # 1. Проверка обязательных полей
        if missing required fields:
            skip

        # 2. Дедупликация по времени (БАГ #12 ИСПРАВЛЕН)
        if candle.time in seen_times:
            skip
        seen_times.add(candle.time)

        # 3. Логичность OHLC
        if NOT (low <= open <= high AND low <= close <= high):
            skip

        # 4. Положительные цены
        if any(price <= 0):
            skip

        valid_candles.append(candle)

    return valid_candles
```

**Выходные данные:**
- Запись в `candles`:
  ```
  - instrument_id (figi), interval, time
  - open, high, low, close, volume
  ```
- Unique constraint: (instrument_id, interval, time)

**Критические точки:**
- ✅ ИСПРАВЛЕНО: Retry logic с exponential backoff
- ✅ ИСПРАВЛЕНО: Rate limiting (100 req/min)
- ✅ ИСПРАВЛЕНО: Timeout для каждого запроса (30-60s)
- ✅ ИСПРАВЛЕНО: Дедупликация свечей по времени
- ⚠️ Sandbox/Production mode через env var

---

### ФАЗА 5: Бэктестинг консенсусов

```
┌─────────────────────────────────────────────────────────┐
│ 5. CONSENSUS BACKTESTER                                 │
│    tbot/analysis/consensus_backtester.py                │
└─────────────────────────────────────────────────────────┘
```

**Что происходит:**
1. Симуляция торговли по консенсусам на исторических данных
2. Расчет P&L с учетом риск-менеджмента
3. Оценка эффективности правил консенсуса

**Алгоритм бэктеста:**

```python
def run_backtest(rule_id, start_date, end_date, params):
    # ВАЛИДАЦИЯ (БАГ #11 ИСПРАВЛЕН)
    if take_profit_pct <= 0 OR > 100: raise ValueError
    if stop_loss_pct <= 0 OR > 100: raise ValueError
    if initial_capital <= 0: raise ValueError
    # ...

    capital = initial_capital
    results = []

    # 1. Загрузить все сигналы в периоде
    signals = SELECT * FROM parsed_signals WHERE:
        - timestamp BETWEEN start_date AND end_date
        - signal_type = 'entry'
        - ticker IN tickers (if specified)

    # 2. Детектировать консенсусы (используя правило)
    consensus_events = []
    processed_signals = set()

    for signal in signals:
        if signal.id in processed_signals:
            continue

        consensus_data = detector._find_consensus_window(
            signal, rule.window_minutes, rule.min_traders, rule
        )

        if consensus_data:
            # Помечаем все сигналы консенсуса
            for cs in consensus_data.signals:
                processed_signals.add(cs.id)

            consensus_events.append({
                ticker, direction, timestamp,
                traders_count, avg_price
            })

    # 3. Симулировать каждую сделку
    for event in consensus_events:
        result = _simulate_trade(event, capital, params)
        if result:
            capital += result.profit_abs  # Обновляем капитал
            result.capital_after = capital
            results.append(result)

    # 4. Агрегировать статистику
    stats = _calculate_statistics(results, initial_capital)

    # 5. Сохранить в БД
    INSERT INTO consensus_backtests (
        rule_id, start_date, end_date,
        total_consensus_found, profitable_count, loss_count,
        win_rate, avg_profit_pct, total_return_pct,
        results_by_ticker, consensus_details
    )

    return {backtest_id, stats, results, final_capital}
```

**Симуляция одной сделки:**

```python
def _simulate_trade(event, capital, params):
    # 1. Получить FIGI
    figi = SELECT figi FROM instruments WHERE ticker = event.ticker

    # 2. Найти цену входа (первая свеча после консенсуса)
    entry_candle = SELECT * FROM candles WHERE:
        - instrument_id = figi
        - time >= event.timestamp
        - interval = 'hour'
    ORDER BY time LIMIT 1

    if NOT entry_candle:
        return None  # Нет данных

    entry_price = entry_candle.close

    # 3. Рассчитать размер позиции
    position_value = capital * (position_size_pct / 100)
    shares = int(position_value / entry_price)

    if shares <= 0:  # БАГ #6 ИСПРАВЛЕН
        return None

    # 4. Установить уровни выхода
    if direction == 'long':
        take_profit_price = entry_price * (1 + take_profit_pct/100)
        stop_loss_price = entry_price * (1 - stop_loss_pct/100)
    else:  # short
        take_profit_price = entry_price * (1 - take_profit_pct/100)
        stop_loss_price = entry_price * (1 + stop_loss_pct/100)

    # 5. Симулировать движение цены
    exit_time = entry_time + holding_hours
    candles = SELECT * FROM candles WHERE:
        - instrument_id = figi
        - time > entry_candle.time
        - time <= exit_time
        - interval = 'hour'
    ORDER BY time

    # БАГ #2 ИСПРАВЛЕН: Обработка отсутствия данных
    if NOT candles:
        last_candle = SELECT * FROM candles WHERE:
            - instrument_id = figi
            - time > entry_candle.time
        ORDER BY time DESC LIMIT 1

        if last_candle:
            exit_price = last_candle.close
            exit_reason = 'timeout'
        else:
            return None  # Пропускаем сделку без данных

    else:
        # Проходим по свечам, ищем триггеры
        for candle in candles:
            if direction == 'long':
                if candle.high >= take_profit_price:
                    exit_price = take_profit_price
                    exit_reason = 'take_profit'
                    break
                if candle.low <= stop_loss_price:
                    exit_price = stop_loss_price
                    exit_reason = 'stop_loss'
                    break
            # То же для short...

            exit_price = candle.close  # Если не сработал TP/SL
            exit_reason = 'timeout'

    # 6. Рассчитать P&L
    if direction == 'long':
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
    else:
        pnl_pct = ((entry_price - exit_price) / entry_price) * 100

    profit_abs = shares * entry_price * (pnl_pct / 100)

    return {
        ticker, direction,
        entry_time, exit_time,
        entry_price, exit_price,
        shares, position_value,
        pnl_pct, profit_abs,
        exit_reason, traders_count
    }
```

**Выходные данные:**
- Объект в памяти с результатами
- Запись в `consensus_backtests` с полной статистикой
- Детали каждой сделки в JSON `consensus_details`

**Критические точки:**
- ✅ ИСПРАВЛЕНО: Пропуск сделок без данных вместо P&L=0
- ✅ ИСПРАВЛЕНО: Проверка shares <= 0
- ✅ ИСПРАВЛЕНО: Валидация всех входных параметров
- ✅ Динамическое обновление капитала после каждой сделки
- ⚠️ Риск-менеджмент: Stop Loss, Take Profit, Position Sizing

---

### ФАЗА 6: Отслеживание позиций (Live Trading)

```
┌─────────────────────────────────────────────────────────┐
│ 6. SIGNAL MATCHER                                       │
│    tbot/analysis/signal_matcher.py                      │
└─────────────────────────────────────────────────────────┘
```

**Что происходит:**
1. Отслеживание необработанных сигналов
2. Поиск цен входа через API или БД
3. Мониторинг активных позиций на предмет выхода

**Алгоритм обработки:**

```python
async def process_untracked_signals(limit=50):
    # 1. Получить необработанные сигналы
    untracked = SELECT * FROM parsed_signals WHERE:
        - id NOT IN (SELECT signal_id FROM signal_results)
        - direction IN ('long', 'short')
        - timestamp >= NOW() - 7 days
    ORDER BY timestamp LIMIT {limit}

    for signal in untracked:
        # 2. Убедиться что инструмент есть в БД
        figi = await ensure_instrument_in_database(signal.ticker)
        if NOT figi:
            # Попытка загрузить через API
            api_instrument = await tinkoff.find_instrument_by_ticker(ticker)
            if api_instrument:
                INSERT INTO instruments (...)
                figi = api_instrument.figi
            else:
                continue  # Не найден

        # 3. Найти цену входа
        entry_match = await _find_entry_price(signal, figi)

        if entry_match:
            # 4. Создать результат отслеживания
            INSERT INTO signal_results (
                signal_id,
                planned_entry_price = signal.target_price,
                actual_entry_price = entry_match.actual_price,
                entry_time = entry_match.price_time,
                status = 'active'
            )

async def _find_entry_price(signal, figi):
    signal_time = signal.timestamp
    search_end = signal_time + 1 hour

    # ПОПЫТКА 1: Поиск в БД
    candles = SELECT * FROM candles WHERE:
        - instrument_id = figi
        - interval = '5min'
        - time >= signal_time
        - time <= search_end
    ORDER BY time LIMIT 12

    if candles:
        entry_price = candles[0].open
        entry_time = candles[0].time
    else:
        # ПОПЫТКА 2: API (с retry + rate limiting + timeout)
        if NOT tinkoff:
            return None

        price_data = await tinkoff.get_current_price(ticker)
        if NOT price_data:
            return None

        entry_price = price_data.price
        entry_time = NOW()

    # Рассчитать проскальзывание
    slippage_pct = ((entry_price - target_price) / target_price) * 100

    return PriceMatch(
        signal_id, signal_time, target_price,
        entry_price, entry_time, slippage_pct, delay_minutes
    )
```

**Мониторинг активных позиций:**

```python
async def update_active_positions():
    # БАГ #3 ИСПРАВЛЕН: SELECT FOR UPDATE для предотвращения race conditions
    WITH db.session() as session:
        results = SELECT * FROM signal_results WHERE:
            - status = 'active'
        FOR UPDATE SKIP LOCKED  # Пропускаем заблокированные строки

        for position in results:
            signal = GET signal_by_id(position.signal_id)
            figi = await ensure_instrument_in_database(signal.ticker)

            # Проверить условия выхода
            current_price = await _get_current_price(figi, signal.ticker)

            # Stop Loss
            if signal.stop_loss:
                if (direction=='long' AND current_price <= stop_loss) OR
                   (direction=='short' AND current_price >= stop_loss):
                    UPDATE signal_results SET:
                        exit_price = current_price
                        exit_time = NOW()
                        exit_reason = 'stop_loss'
                        status = 'closed'

            # Take Profit
            if signal.take_profit:
                if (direction=='long' AND current_price >= take_profit) OR
                   (direction=='short' AND current_price <= take_profit):
                    UPDATE signal_results SET:
                        exit_price = current_price
                        exit_time = NOW()
                        exit_reason = 'take_profit'
                        status = 'closed'

            # Timeout (24 часа по умолчанию)
            if position.tracking_started_at + 24 hours < NOW():
                UPDATE signal_results SET:
                    exit_price = current_price
                    exit_time = NOW()
                    exit_reason = 'timeout'
                    status = 'closed'
```

**Критические точки:**
- ✅ ИСПРАВЛЕНО: SELECT FOR UPDATE SKIP LOCKED (race conditions)
- ✅ Двухэтапный поиск цен: БД → API
- ✅ Retry + Rate Limiting + Timeout для API
- ⚠️ Таймаут позиций: 24 часа

---

### ФАЗА 7: API & Веб-интерфейс

```
┌─────────────────────────────────────────────────────────┐
│ 7. FASTAPI APPLICATION                                  │
│    tbot/api/app.py                                      │
└─────────────────────────────────────────────────────────┘
```

**Основные эндпоинты:**

```
# Консенсусы
GET    /api/consensus/rules
POST   /api/consensus/rules
PUT    /api/consensus/rules/{id}
DELETE /api/consensus/rules/{id}
GET    /api/consensus/detections
POST   /api/consensus/detect

# Бэктесты
POST   /api/consensus/backtest
GET    /api/consensus/backtest/{id}

# Сигналы
GET    /api/signals?ticker=SBER&direction=long&status=active
GET    /api/signals/stats

# Telegram
POST   /api/telegram/channels
GET    /api/telegram/channels
POST   /api/telegram/start_scraping
POST   /api/telegram/stop_scraping

# Мониторинг
GET    /api/health
GET    /api/stats
```

---

## 🗄️ БАЗА ДАННЫХ

### Основные таблицы:

```sql
raw_messages (сырые сообщения)
  ↓
parsed_signals (распознанные сигналы)
  ↓
consensus_events (найденные консенсусы)
  ↓
consensus_signals (связь N:M)

signal_results (отслеживание позиций)

candles (рыночные данные)
instruments (инструменты)
consensus_rules (правила детекции)
consensus_backtests (результаты тестов)
```

---

## ⚙️ КРИТИЧЕСКИЕ КОМПОНЕНТЫ

### Thread Safety:
- ✅ Singleton с double-check locking
- ✅ SELECT FOR UPDATE для активных позиций
- ✅ Deadlock retry с exponential backoff

### API Resilience:
- ✅ Retry logic (3 попытки, exp backoff)
- ✅ Rate limiting (100 req/min)
- ✅ Timeouts (30-60s)
- ✅ Дедупликация данных

### Data Validation:
- ✅ Входные параметры бэктеста
- ✅ OHLC свечей
- ✅ Уникальность по времени
- ✅ Положительные значения

---

## 🚀 ГОТОВНОСТЬ К ПРОДАКШЕНУ

### Исправленные баги:
1. ✅ Async/Sync mismatch
2. ✅ Silent failure при отсутствии данных
3. ✅ Race conditions в SignalMatcher
4. ✅ Retry logic для API
5. ✅ False positive при нехватке данных
6. ✅ Проверка отрицательных shares
7. ✅ Rate limiting
8. ✅ Timeout обработка
9. ✅ Deadlock retry
10. ✅ Thread-safe singleton
11. ✅ Валидация входных данных
12. ✅ Дедупликация свечей

### Что еще нужно:
- ⚠️ Централизованное логирование (Sentry)
- ⚠️ Мониторинг метрик (Prometheus)
- ⚠️ Алерты (PagerDuty/Telegram)
- ⚠️ Юнит-тесты (coverage > 70%)
- ⚠️ Graceful shutdown
- ⚠️ Circuit breaker pattern
- ⚠️ Secrets management

---

## 📊 ПРИМЕР ПОЛНОГО ПОТОКА

```
1. Telegram сообщение: "🔥 SBER покупка @ 280₽, цель 290₽, стоп 275₽ - Иван"
   ↓
2. Сохранение: raw_messages (id=123, text="...", is_processed=FALSE)
   ↓
3. Парсинг: parsed_signals (
      ticker="SBER", direction="long", target_price=280,
      take_profit=290, stop_loss=275, author="Иван"
   )
   ↓
4. Проверка консенсуса: Найдены еще 2 сигнала от "Петр" и "Мария" на SBER long
   ↓
5. Создание консенсуса: consensus_events (
      ticker="SBER", direction="long", traders_count=3,
      avg_entry_price=279, consensus_strength=75
   )
   ↓
6. Проверка индикаторов: RSI=35 (перепродан), MACD=bullish → ОК
   ↓
7. Бэктест (опционально): Тест на истории → Win rate=68%, Avg profit=3.2%
   ↓
8. Live tracking: Ожидание цены входа, мониторинг TP/SL
   ↓
9. Выход: Take profit достигнут @ 290₽, P&L = +3.6%
   ↓
10. Результат: signal_results (status='closed', profit_loss_pct=3.6)
```

---

**Документ создан:** 2024
**Версия системы:** TBOT_V2
**Статус:** Production-ready после исправления критических багов
