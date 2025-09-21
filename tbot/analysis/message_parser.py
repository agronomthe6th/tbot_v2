# analysis/message_parser.py
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ParseResult:
    """Результат парсинга сообщения"""
    success: bool
    signal_data: Optional[Dict] = None
    error: Optional[str] = None
    confidence: float = 0.0

class MessageParser:
    """Простой и четкий парсер торговых сигналов"""
    
    VERSION = "2.0.0"
    
    def __init__(self):
        # Паттерны для тикеров - простые и четкие
        self.ticker_patterns = [
            r':\s*([A-Z]{3,6})\b',         # ": SPBE" - основной паттерн
            r'\$([A-Z]{3,6})\b',           # "$SBER"
            r'\b([A-Z]{3,6})\b(?=\s|$)',   # "SBER " - отдельно стоящий
        ]
        
        # ПРОСТЫЕ правила определения направления
        self.entry_patterns = {
            'long': [
                r'(?i)\b(вход|купил|покупк|buy|набрал)\s+лонг\b',
                r'(?i)\b(открыл|взял)\s+лонг\b',
                r'(?i)\b(лонг|long)\s+(по|от|в|@)',  # "лонг по цене"
            ],
            'short': [
                r'(?i)\b(вход|продал|продаж|sell|набрал)\s+шорт\b',
                r'(?i)\b(открыл|взял)\s+шорт\b',
                r'(?i)\b(шорт|short)\s+(по|от|в|@)',  # "шорт по цене"
            ]
        }
        
        # ЧЕТКИЕ правила для выхода/изменения позиций
        self.exit_patterns = [
            r'(?i)\b(сократил|уменьшил|reduce)\s+(лонг|шорт|long|short)\b',  # "сократил лонг"
            r'(?i)\b(увеличил|добавил|add)\s+(лонг|шорт|long|short)\b',      # "увеличил лонг"
            r'(?i)\b(закрыл|фикс|взял|close)\s*(лонг|шорт|long|short)?\b',   # "закрыл лонг"
            r'(?i)\b(выход|exit)\s*(из)?\s*(лонг|шорт|long|short)?\b',       # "выход из лонга"
            r'(?i)\b(стоп|stop)\s*(по)?\s*(лонг|шорт|long|short)?\b',        # "стоп по лонгу"
            r'(?i)(лонг|шорт|long|short)\s*🐃\s*:',                          # "лонг🐃:"
            r'(?i)(лонг|шорт|long|short)\s*🐻\s*:',                          # "шорт🐻:"
        ]
        
        # Простые торговые ключевые слова
        self.trading_keywords = [
            r'(?i)\b(сделка|позиция|сигнал)\b',
            r'(?i)\b(лонг|шорт|long|short)\b',
            r'(?i)\b(сократил|увеличил|закрыл|открыл)\b',
            r'(?i)\b(купил|продал|buy|sell)\b',
        ]
        
        # Паттерны для автора
        self.author_patterns = [
            r'#([A-Za-z0-9_]+)\s*[-–]',    # "#ProfitKing -" или "#ProfitKing –"
            r'#([A-Za-z0-9_]+)\b',         # просто "#ProfitKing"
        ]
    
    def parse_raw_message(self, raw_message: Dict) -> ParseResult:
        """Основной метод парсинга"""
        try:
            text = raw_message.get('text', '')
            if not text or not text.strip():
                return ParseResult(success=False, error="Empty message text")
            
            # Очищаем мусор
            cleaned_text = self._clean_message_text(text)
            logger.debug(f"Cleaned text: {cleaned_text}")
            
            # Проверяем торговое ли сообщение
            if not self._is_trading_message(cleaned_text):
                return ParseResult(success=False, error="Not a trading message")
            
            # Извлекаем основные компоненты
            ticker = self._extract_ticker(cleaned_text)
            if not ticker:
                return ParseResult(success=False, error="No ticker found")
            
            # Определяем тип операции и направление
            operation_type, direction = self._analyze_operation(cleaned_text)
            
            author = self._extract_author(cleaned_text, raw_message.get('author_username'))
            prices = self._extract_prices(cleaned_text)
            confidence = self._calculate_confidence(cleaned_text, ticker, direction, operation_type)
            
            # Формируем результат
            signal_data = {
                'raw_message_id': raw_message['id'],
                'parser_version': self.VERSION,
                'timestamp': raw_message['timestamp'],
                'channel_id': raw_message['channel_id'],
                'author': author,
                'original_text': text,
                'ticker': ticker,
                'direction': direction,
                'signal_type': operation_type,
                'target_price': prices.get('target'),
                'stop_loss': prices.get('stop_loss'),
                'take_profit': prices.get('take_profit'),
                'confidence_score': confidence,
                'extracted_data': {
                    'cleaned_text': cleaned_text,
                    'operation_analysis': self._debug_operation_analysis(cleaned_text),
                    'all_tickers': self._extract_all_tickers(cleaned_text),
                    'all_prices': self._extract_all_numbers(cleaned_text),
                    'raw_message_id': raw_message['id']
                }
            }
            
            logger.info(f"✅ Parsed message {raw_message['id']}: "
                       f"ticker={ticker}, direction={direction}, operation={operation_type}, confidence={confidence}")
            
            return ParseResult(success=True, signal_data=signal_data, confidence=confidence)
            
        except Exception as e:
            logger.error(f"❌ Error parsing message {raw_message.get('id')}: {e}")
            return ParseResult(success=False, error=f"Exception: {str(e)}")
    
    def _clean_message_text(self, text: str) -> str:
        """Очистка мусора из сообщения"""
        cleaned = text
        
        # Удаляем мусорные части
        garbage_patterns = [
            r'Больше информации.*?(?=\n|$)',          # "Больше информации..."
            r'👉\[@копии.*?\].*?(?=\n|$)',           # Ссылки на копии
            r'\[.*?\]\(https://t\.me/.*?\)',         # Markdown ссылки
            r'https://t\.me/\S+',                    # Прямые ссылки
            r'@\w+_?bot\S*',                         # Боты
        ]
        
        for pattern in garbage_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Убираем лишние пробелы
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _is_trading_message(self, text: str) -> bool:
        """Простая проверка на торговое сообщение"""
        # Есть торговые ключевые слова?
        has_keywords = any(re.search(pattern, text) for pattern in self.trading_keywords)
        
        # Есть тикер?
        has_ticker = any(re.search(pattern, text) for pattern in self.ticker_patterns)
        
        # Есть торговые эмодзи?
        trading_emojis = ['🐃', '🐻', '📈', '📉', '⭐️']
        has_emoji = any(emoji in text for emoji in trading_emojis)
        
        result = has_keywords or has_ticker or has_emoji
        
        logger.debug(f"Trading check: keywords={has_keywords}, ticker={has_ticker}, "
                    f"emoji={has_emoji} -> {result}")
        
        return result
    
    def _extract_ticker(self, text: str) -> Optional[str]:
        """Извлечение тикера"""
        for pattern in self.ticker_patterns:
            match = re.search(pattern, text)
            if match:
                ticker = match.group(1).upper()
                if 3 <= len(ticker) <= 6 and ticker.isalpha():
                    # Исключаем ложные срабатывания
                    if ticker not in ['VIP', 'BOT', 'NEW', 'TOP', 'WIN', 'BUY', 'SELL']:
                        logger.debug(f"Found ticker: {ticker}")
                        return ticker
        return None
    
    def _extract_all_tickers(self, text: str) -> List[str]:
        """Все найденные тикеры"""
        tickers = set()
        for pattern in self.ticker_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                ticker = match.upper()
                if 3 <= len(ticker) <= 6 and ticker.isalpha():
                    if ticker not in ['VIP', 'BOT', 'NEW', 'TOP', 'WIN', 'BUY', 'SELL']:
                        tickers.add(ticker)
        return list(tickers)
    
    def _analyze_operation(self, text: str) -> Tuple[str, str]:
        """
        Анализ операции - КЛЮЧЕВАЯ ЛОГИКА
        
        Returns:
            Tuple[operation_type, direction] где:
            operation_type: 'entry' | 'exit' | 'update'
            direction: 'long' | 'short' | 'mixed'
        """
        
        # 1. Проверяем EXIT/UPDATE операции (приоритет!)
        for pattern in self.exit_patterns:
            match = re.search(pattern, text)
            if match:
                logger.debug(f"Found exit pattern: {pattern} -> {match.group()}")
                
                # Определяем направление из контекста
                if re.search(r'(?i)(лонг|long)', match.group()):
                    return 'exit', 'long'  # Сократил лонг = продал длинную позицию
                elif re.search(r'(?i)(шорт|short)', match.group()):
                    return 'exit', 'short'  # Сократил шорт = закрыл короткую позицию
                else:
                    return 'exit', 'mixed'  # Неопределенное направление
        
        # 2. Проверяем ENTRY операции
        for direction, patterns in self.entry_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    logger.debug(f"Found entry pattern for {direction}: {pattern}")
                    return 'entry', direction
        
        # 3. Если ничего не нашли, но есть упоминания лонг/шорт
        if re.search(r'(?i)\b(лонг|long)\b', text):
            return 'entry', 'long'  # По умолчанию считаем входом
        elif re.search(r'(?i)\b(шорт|short)\b', text):
            return 'entry', 'short'
        
        # 4. Совсем ничего не нашли
        return 'entry', 'mixed'
    
    def _debug_operation_analysis(self, text: str) -> Dict:
        """Отладочная информация для анализа операций"""
        debug_info = {
            'exit_matches': [],
            'entry_matches': [],
            'direction_words': []
        }
        
        # Проверяем exit паттерны
        for pattern in self.exit_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                debug_info['exit_matches'].append({'pattern': pattern, 'matches': matches})
        
        # Проверяем entry паттерны
        for direction, patterns in self.entry_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    debug_info['entry_matches'].append({
                        'direction': direction, 
                        'pattern': pattern, 
                        'matches': matches
                    })
        
        # Ищем слова направлений
        direction_words = re.findall(r'(?i)\b(лонг|шорт|long|short)\b', text)
        debug_info['direction_words'] = direction_words
        
        return debug_info
    
    def _extract_author(self, text: str, fallback: Optional[str] = None) -> str:
        """Извлечение автора"""
        for pattern in self.author_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return fallback or 'Unknown'
    
    def _extract_prices(self, text: str) -> Dict[str, Optional[float]]:
        """Извлечение цен (пока простая версия)"""
        prices = {'target': None, 'stop_loss': None, 'take_profit': None}
        
        # Ищем числа с контекстом
        price_patterns = {
            'target': [
                r'(?:цел|target|таргет|@)\s*:?\s*(\d+(?:[.,]\d+)?)',
                r'(?:по|от)\s+(\d+(?:[.,]\d+)?)',
            ],
            'stop_loss': [
                r'(?:стоп|stop)\s*:?\s*(\d+(?:[.,]\d+)?)',
            ],
            'take_profit': [
                r'(?:тейк|take|профит)\s*:?\s*(\d+(?:[.,]\d+)?)',
            ]
        }
        
        for price_type, patterns in price_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        price = float(match.group(1).replace(',', '.'))
                        if 0.01 <= price <= 100000:
                            prices[price_type] = price
                            break
                    except ValueError:
                        continue
        
        return prices
    
    def _extract_all_numbers(self, text: str) -> List[float]:
        """Все числа из текста"""
        numbers = []
        for match in re.finditer(r'\d+(?:[.,]\d+)?', text):
            try:
                number = float(match.group().replace(',', '.'))
                if 0.01 <= number <= 100000:
                    numbers.append(number)
            except ValueError:
                continue
        return numbers
    
    def _calculate_confidence(self, text: str, ticker: str, direction: str, operation: str) -> float:
        """Расчет уверенности"""
        confidence = 0.0
        
        # Базовые компоненты
        if ticker:
            confidence += 0.4
        if direction and direction != 'mixed':
            confidence += 0.3
        if operation:
            confidence += 0.2
        
        # Бонусы
        if len(text.split()) > 3:
            confidence += 0.05
        if any(keyword in text.lower() for keyword in ['сделка', 'позиция', 'сигнал']):
            confidence += 0.05
        
        return min(confidence, 1.0)

class MessageParsingService:
    """Сервис для массовой обработки сообщений"""
    
    def __init__(self, db_manager, parser: MessageParser = None):
        self.db = db_manager
        self.parser = parser or MessageParser()
    
    def parse_all_unprocessed_messages(self, limit: Optional[int] = None) -> Dict:
        """Обработка всех неразобранных сообщений"""
        try:
            unprocessed = self._get_unprocessed_messages(limit)
            
            stats = {
                'total_processed': 0,
                'successful_parses': 0,
                'failed_parses': 0,
                'trading_messages': 0,
                'non_trading_messages': 0,
                'errors': []
            }
            
            logger.info(f"Starting to parse {len(unprocessed)} messages...")
            
            for message in unprocessed:
                try:
                    stats['total_processed'] += 1
                    
                    result = self.parser.parse_raw_message(message)
                    
                    if result.success:
                        signal_id = self.db.save_signal(result.signal_data)
                        if signal_id:
                            stats['successful_parses'] += 1
                            stats['trading_messages'] += 1
                        else:
                            stats['failed_parses'] += 1
                    else:
                        stats['failed_parses'] += 1
                        if result.error != "Not a trading message":
                            stats['errors'].append(f"Message {message['id']}: {result.error}")
                        else:
                            stats['non_trading_messages'] += 1
                    
                    self._mark_message_processed(message['id'])
                    
                    if stats['total_processed'] % 50 == 0:
                        logger.info(f"Processed {stats['total_processed']}/{len(unprocessed)}...")
                
                except Exception as e:
                    stats['failed_parses'] += 1
                    stats['errors'].append(f"Message {message['id']}: {str(e)}")
                    logger.error(f"Error processing message {message['id']}: {e}")
            
            logger.info(f"Parsing completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in parse_all_unprocessed_messages: {e}")
            return {'error': str(e)}
    
    def _get_unprocessed_messages(self, limit: Optional[int] = None) -> List[Dict]:
        """Получение неразобранных сообщений"""
        try:
            with self.db.session() as session:
                from core.database import RawMessage
                
                query = session.query(RawMessage).filter(
                    RawMessage.is_processed == False,
                    RawMessage.text.isnot(None),
                    RawMessage.text != ''
                ).order_by(RawMessage.timestamp)
                
                if limit:
                    query = query.limit(limit)
                
                messages = query.all()
                
                return [
                    {
                        'id': msg.id,
                        'text': msg.text,
                        'timestamp': msg.timestamp,
                        'channel_id': msg.channel_id,
                        'author_username': msg.author_username,
                        'message_id': msg.message_id
                    }
                    for msg in messages
                ]
        except Exception as e:
            logger.error(f"Error getting unprocessed messages: {e}")
            return []
    
    def _mark_message_processed(self, message_id: int) -> bool:
        """Пометка сообщения как обработанного"""
        try:
            with self.db.session() as session:
                from core.database import RawMessage
                
                message = session.query(RawMessage).filter(
                    RawMessage.id == message_id
                ).first()
                
                if message:
                    message.is_processed = True
                    message.processing_attempts = (message.processing_attempts or 0) + 1
                    return True
                
                return False
        except Exception as e:
            logger.error(f"Error marking message as processed: {e}")
            return False