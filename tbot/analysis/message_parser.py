import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from uuid import UUID

from .pattern_manager import PatternManager
from .consensus_detector import get_consensus_detector

logger = logging.getLogger(__name__)

@dataclass
class ParseResult:
    """Результат парсинга сообщения"""
    success: bool
    signal_data: Optional[Dict] = None
    error: Optional[str] = None
    confidence: float = 0.0


class MessageParser:
    """Парсер торговых сигналов с поддержкой паттернов из БД"""
    
    VERSION = "3.1.0"
    
    def __init__(self, db_manager=None):
        """
        Инициализация парсера
        
        Args:
            db_manager: Database instance для загрузки паттернов из БД
        """
        self.db_manager = db_manager
        
        if db_manager:
            self.pattern_manager = PatternManager(db_manager)
            logger.info(f"MessageParser v{self.VERSION} initialized with PatternManager (DB mode)")
        else:
            self.pattern_manager = None
            logger.warning(f"MessageParser v{self.VERSION} initialized WITHOUT database")
    
    def reload_patterns(self):
        """Перезагрузить паттерны из БД"""
        if self.pattern_manager:
            self.pattern_manager.reload_patterns()
            logger.info("Patterns reloaded from database")
        else:
            logger.warning("Cannot reload patterns - no database connection")
    
    def parse_raw_message(self, raw_message: Dict) -> ParseResult:
        """
        Основной метод парсинга сообщения
        
        Args:
            raw_message: словарь с данными сообщения
            
        Returns:
            ParseResult: результат парсинга
        """
        try:
            text = raw_message.get('text', '')
            if not text or not text.strip():
                return ParseResult(success=False, error="Empty message text")
            
            logger.debug(f"📝 Parsing message {raw_message.get('id')}")
            logger.debug(f"Original text: {text[:200]}")
            
            # ИЗВЛЕКАЕМ АВТОРА ИЗ ОРИГИНАЛЬНОГО ТЕКСТА (ДО ОЧИСТКИ!)
            author = self._extract_author(text, raw_message.get('author_username'))
            logger.debug(f"👤 Extracted author: {author}")
            
            # Базовая очистка без удаления хештегов
            cleaned_text = text.strip()
            
            if not self._is_trading_message(cleaned_text):
                return ParseResult(success=False, error="Not a trading message")
            
            ticker = self._extract_ticker(cleaned_text)
            if not ticker:
                return ParseResult(success=False, error="No ticker found")
            
            operation_type, direction = self._analyze_operation(cleaned_text)
            
            prices = self._extract_prices(cleaned_text)
            confidence = self._calculate_confidence(cleaned_text, ticker, direction, operation_type)
            
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
                       f"ticker={ticker}, direction={direction}, operation={operation_type}, "
                       f"author={author}, confidence={confidence}")
            
            return ParseResult(success=True, signal_data=signal_data, confidence=confidence)
            
        except Exception as e:
            logger.error(f"❌ Error parsing message {raw_message.get('id')}: {e}", exc_info=True)
            return ParseResult(success=False, error=f"Exception: {str(e)}")
    
    def _clean_message_text(self, text: str) -> str:
        """
        Очистка мусора из сообщения
        ВРЕМЕННО ОТКЛЮЧЕНА для отладки
        
        Args:
            text: исходный текст
            
        Returns:
            str: очищенный текст
        """
        if not self.pattern_manager:
            return text.strip()
        
        cleaned = text
        
        # Закомментировано для отладки
        # garbage_patterns = self.pattern_manager.get_patterns('garbage')
        # for pattern in garbage_patterns:
        #     cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _is_trading_message(self, text: str) -> bool:
        """
        Проверка является ли сообщение торговым
        
        Args:
            text: текст сообщения
            
        Returns:
            bool: True если торговое сообщение
        """
        if not self.pattern_manager:
            return False
        
        trading_keywords = self.pattern_manager.get_patterns('trading_keyword')
        ticker_patterns = self.pattern_manager.get_patterns('ticker')
        
        has_keywords = any(re.search(pattern, text, re.IGNORECASE) for pattern in trading_keywords)
        has_ticker = any(re.search(pattern, text) for pattern in ticker_patterns)
        
        trading_emojis = ['🔥', '🎪', '📈', '📉', '⭐']
        has_emoji = any(emoji in text for emoji in trading_emojis)
        
        result = has_keywords or has_ticker or has_emoji
        
        logger.debug(f"Trading check: keywords={has_keywords}, ticker={has_ticker}, "
                    f"emoji={has_emoji} -> {result}")
        
        return result
    
    def _extract_ticker(self, text: str) -> Optional[str]:
        """
        Извлечение тикера из текста
        
        Args:
            text: текст сообщения
            
        Returns:
            Optional[str]: найденный тикер или None
        """
        if not self.pattern_manager:
            return None
        
        ticker_patterns = self.pattern_manager.get_patterns('ticker')
        
        for pattern in ticker_patterns:
            match = re.search(pattern, text)
            if match:
                ticker = match.group(1).upper()
                logger.debug(f"Found ticker: {ticker} with pattern: {pattern}")
                return ticker
        
        return None
    
    def _extract_all_tickers(self, text: str) -> List[str]:
        """
        Извлечение всех тикеров из текста
        
        Args:
            text: текст сообщения
            
        Returns:
            List[str]: список найденных тикеров
        """
        if not self.pattern_manager:
            return []
        
        ticker_patterns = self.pattern_manager.get_patterns('ticker')
        
        tickers = set()
        for pattern in ticker_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                ticker = match.upper()
                if 3 <= len(ticker) <= 6 and ticker.isalpha():
                    if ticker not in ['VIP', 'BOT', 'NEW', 'TOP', 'WIN', 'BUY', 'SELL']:
                        tickers.add(ticker)
        
        return list(tickers)
    
    def _analyze_operation(self, text: str) -> Tuple[str, str]:
        """
        Анализ операции - определение типа и направления
        
        Args:
            text: текст сообщения
            
        Returns:
            Tuple[str, str]: (operation_type, direction)
                operation_type: 'entry' | 'exit' | 'update'
                direction: 'long' | 'short' | 'mixed'
        """
        if not self.pattern_manager:
            return 'entry', 'mixed'
        
        exit_patterns = self.pattern_manager.get_patterns('operation_exit')
        
        for pattern in exit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                logger.debug(f"Found exit pattern: {pattern} -> {match.group()}")
                
                if re.search(r'(?i)(лонг|long)', match.group()):
                    return 'exit', 'long'
                elif re.search(r'(?i)(шорт|short)', match.group()):
                    return 'exit', 'short'
                else:
                    return 'exit', 'mixed'
        
        long_patterns = self.pattern_manager.get_patterns('direction_long')
        short_patterns = self.pattern_manager.get_patterns('direction_short')
        
        for pattern in long_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(f"Found long entry pattern: {pattern}")
                return 'entry', 'long'
        
        for pattern in short_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(f"Found short entry pattern: {pattern}")
                return 'entry', 'short'
        
        if re.search(r'(?i)\b(лонг|long)\b', text):
            return 'entry', 'long'
        elif re.search(r'(?i)\b(шорт|short)\b', text):
            return 'entry', 'short'
        
        return 'entry', 'mixed'
    
    def _debug_operation_analysis(self, text: str) -> Dict:
        """
        Отладочная информация для анализа операций
        
        Args:
            text: текст сообщения
            
        Returns:
            Dict: информация о совпадениях паттернов
        """
        if not self.pattern_manager:
            return {}
        
        debug_info = {
            'exit_matches': [],
            'long_matches': [],
            'short_matches': [],
            'direction_words': []
        }
        
        exit_patterns = self.pattern_manager.get_patterns('operation_exit')
        for pattern in exit_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                debug_info['exit_matches'].append({'pattern': pattern, 'matches': matches})
        
        long_patterns = self.pattern_manager.get_patterns('direction_long')
        for pattern in long_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                debug_info['long_matches'].append({'pattern': pattern, 'matches': matches})
        
        short_patterns = self.pattern_manager.get_patterns('direction_short')
        for pattern in short_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                debug_info['short_matches'].append({'pattern': pattern, 'matches': matches})
        
        direction_words = re.findall(r'(?i)\b(лонг|шорт|long|short)\b', text)
        debug_info['direction_words'] = direction_words
        
        return debug_info
    
    def _extract_author(self, text: str, fallback: Optional[str] = None) -> str:
        """
        Извлечение автора из текста
        
        Args:
            text: текст сообщения
            fallback: значение по умолчанию
            
        Returns:
            str: имя автора
        """
        if not self.pattern_manager:
            logger.warning("⚠️ No pattern_manager in _extract_author")
            return fallback or 'Unknown'
        
        author_patterns = self.pattern_manager.get_patterns('author')
        
        logger.debug(f"🔍 Author patterns count: {len(author_patterns)}")
        logger.debug(f"🔍 Text to search (first 150 chars): {text[:150]}")
        
        for i, pattern in enumerate(author_patterns):
            logger.debug(f"🔍 Testing author pattern #{i+1}: {pattern}")
            try:
                match = re.search(pattern, text)
                if match:
                    # Пытаемся взять первую группу, если есть
                    if match.groups():
                        author = match.group(1)
                    else:
                        author = match.group()
                    
                    logger.info(f"✅ Found author: '{author}' with pattern: {pattern}")
                    return author
                else:
                    logger.debug(f"❌ Pattern #{i+1} did not match")
            except Exception as e:
                logger.error(f"❌ Error testing pattern {pattern}: {e}")
                continue
        
        logger.warning(f"⚠️ No author found in text, using fallback: {fallback or 'Unknown'}")
        return fallback or 'Unknown'
    
    def _extract_prices(self, text: str) -> Dict[str, Optional[float]]:
        """
        Извлечение цен из текста
        
        Args:
            text: текст сообщения
            
        Returns:
            Dict: словарь с ценами
        """
        prices = {'target': None, 'stop_loss': None, 'take_profit': None}
        
        if not self.pattern_manager:
            return prices
        
        target_patterns = self.pattern_manager.get_patterns('price_target')
        stop_patterns = self.pattern_manager.get_patterns('price_stop')
        take_patterns = self.pattern_manager.get_patterns('price_take')
        
        price_pattern_groups = {
            'target': target_patterns,
            'stop_loss': stop_patterns,
            'take_profit': take_patterns
        }
        
        for price_type, patterns in price_pattern_groups.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        price_str = match.group(1) if match.groups() else match.group()
                        price = float(price_str.replace(',', '.'))
                        if 0.01 <= price <= 100000:
                            prices[price_type] = price
                            break
                    except (ValueError, IndexError):
                        continue
        
        return prices
    
    def _extract_all_numbers(self, text: str) -> List[float]:
        """
        Извлечение всех чисел из текста
        
        Args:
            text: текст сообщения
            
        Returns:
            List[float]: список чисел
        """
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
        """
        Расчет уверенности в парсинге
        
        Args:
            text: текст сообщения
            ticker: найденный тикер
            direction: направление
            operation: тип операции
            
        Returns:
            float: уровень уверенности (0.0 - 1.0)
        """
        confidence = 0.0
        
        if ticker:
            confidence += 0.4
        if direction and direction != 'mixed':
            confidence += 0.3
        if operation:
            confidence += 0.2
        
        if len(text.split()) > 3:
            confidence += 0.05
        if any(keyword in text.lower() for keyword in ['сделка', 'позиция', 'сигнал']):
            confidence += 0.05
        
        return min(confidence, 1.0)


class MessageParsingService:
    """Сервис для массовой обработки сообщений"""

    def __init__(self, db_manager, parser: MessageParser = None):
        """
        Args:
            db_manager: Database instance
            parser: MessageParser instance (создастся автоматически если не передан)
        """
        self.db = db_manager
        self.parser = parser or MessageParser(db_manager)
        self.consensus_detector = get_consensus_detector(db_manager)
        logger.info("MessageParsingService initialized with consensus detector")
    
    def parse_message(self, message: Dict) -> ParseResult:
        """
        Парсинг одного сообщения
        
        Args:
            message: данные сообщения
            
        Returns:
            ParseResult: результат парсинга
        """
        return self.parser.parse_raw_message(message)

    def parse_all_unprocessed_messages(self, limit: Optional[int] = None) -> Dict:
        try:
            unprocessed = self._get_unprocessed_messages(limit)
            
            if not unprocessed:
                logger.info("No unprocessed messages found")
                return {
                    'total_processed': 0,
                    'successful_parses': 0,
                    'failed_parses': 0,
                    'trading_messages': 0,
                    'non_trading_messages': 0,
                    'errors': []
                }
            
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
                            self.db.mark_message_processed(message['id'], parse_success=True)

                            # Проверяем консенсус для нового сигнала
                            try:
                                signal_uuid = UUID(signal_id) if isinstance(signal_id, str) else signal_id
                                consensus_result = self.consensus_detector.check_new_signal_sync(signal_uuid)
                                if consensus_result:
                                    logger.info(f"🔥 Consensus created: {consensus_result}")
                            except Exception as consensus_error:
                                logger.error(f"Failed to check consensus for signal {signal_id}: {consensus_error}")
                        else:
                            stats['failed_parses'] += 1
                            self.db.mark_message_processed(message['id'], parse_success=False)
                    else:
                        stats['failed_parses'] += 1
                        if result.error != "Not a trading message":
                            stats['errors'].append({
                                'message_id': message['id'],
                                'error': result.error
                            })
                        else:
                            stats['non_trading_messages'] += 1
                        
                        self.db.mark_message_processed(message['id'], parse_success=False)
                    
                except Exception as e:
                    logger.error(f"Error processing message {message.get('id')}: {e}")
                    stats['errors'].append({
                        'message_id': message.get('id'),
                        'error': str(e)
                    })
                    self.db.mark_message_processed(message.get('id'), parse_success=False)
            
            logger.info(f"Parsing completed: {stats['successful_parses']} successful, "
                    f"{stats['failed_parses']} failed")
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to parse messages: {e}")
            return {
                'total_processed': 0,
                'successful_parses': 0,
                'failed_parses': 0,
                'errors': [{'error': str(e)}]
            }

    def _get_unprocessed_messages(self, limit: Optional[int]) -> List[Dict]:
        """Получение необработанных сообщений из БД"""
        messages = self.db.get_unparsed_messages(limit=limit or 100)
        return messages