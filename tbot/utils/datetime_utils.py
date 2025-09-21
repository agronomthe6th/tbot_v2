# utils/datetime_utils.py
"""
Утилиты для работы с датами и временными зонами
Все даты в системе хранятся в UTC как приходят от Tinkoff API
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)

def now_utc() -> datetime:
    """
    Возвращает текущее время в UTC с timezone
    
    Returns:
        datetime: Текущее время в UTC timezone-aware
    """
    return datetime.now(timezone.utc)

def ensure_timezone_aware(dt: Union[datetime, None]) -> Optional[datetime]:
    """
    Конвертирует naive datetime в UTC aware или возвращает None
    
    Args:
        dt: datetime объект или None
        
    Returns:
        datetime: timezone-aware datetime в UTC или None
    """
    if dt is None:
        return None
        
    if dt.tzinfo is None:
        # Если timezone не указан, считаем что это UTC
        logger.debug(f"Converting naive datetime {dt} to UTC")
        return dt.replace(tzinfo=timezone.utc)
    
    return dt

def utc_from_days_ago(days: int) -> datetime:
    """
    Возвращает дату N дней назад в UTC timezone-aware
    
    Args:
        days: Количество дней назад
        
    Returns:
        datetime: Дата в UTC timezone-aware
    """
    return now_utc() - timedelta(days=days)

def utc_from_minutes_ago(minutes: int) -> datetime:
    """
    Возвращает дату N минут назад в UTC timezone-aware
    
    Args:
        minutes: Количество минут назад
        
    Returns:
        datetime: Дата в UTC timezone-aware
    """
    return now_utc() - timedelta(minutes=minutes)

def days_between_utc(start_dt: datetime, end_dt: datetime) -> int:
    """
    Вычисляет количество дней между двумя UTC датами
    
    Args:
        start_dt: Начальная дата (должна быть timezone-aware)
        end_dt: Конечная дата (должна быть timezone-aware)
        
    Returns:
        int: Количество дней
    """
    # Обеспечиваем что обе даты timezone-aware
    start_dt = ensure_timezone_aware(start_dt)
    end_dt = ensure_timezone_aware(end_dt)
    
    if start_dt is None or end_dt is None:
        return 0
        
    return (end_dt - start_dt).days

def is_timezone_aware(dt: datetime) -> bool:
    """
    Проверяет является ли datetime timezone-aware
    
    Args:
        dt: datetime объект
        
    Returns:
        bool: True если timezone-aware
    """
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

def safe_datetime_comparison(dt1: datetime, dt2: datetime) -> Optional[int]:
    """
    Безопасное сравнение datetime объектов с автоматической конвертацией в UTC
    
    Args:
        dt1: Первая дата
        dt2: Вторая дата
        
    Returns:
        int: -1 если dt1 < dt2, 0 если равны, 1 если dt1 > dt2, None при ошибке
    """
    try:
        dt1_utc = ensure_timezone_aware(dt1)
        dt2_utc = ensure_timezone_aware(dt2)
        
        if dt1_utc is None or dt2_utc is None:
            return None
            
        if dt1_utc < dt2_utc:
            return -1
        elif dt1_utc > dt2_utc:
            return 1
        else:
            return 0
            
    except Exception as e:
        logger.error(f"Error comparing datetimes: {e}")
        return None

def format_utc_for_display(dt: datetime, include_timezone: bool = True) -> str:
    """
    Форматирует UTC дату для отображения
    
    Args:
        dt: datetime объект
        include_timezone: Включать ли информацию о timezone
        
    Returns:
        str: Отформатированная строка
    """
    dt_utc = ensure_timezone_aware(dt)
    if dt_utc is None:
        return "Unknown"
        
    if include_timezone:
        return dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        return dt_utc.strftime("%Y-%m-%d %H:%M:%S")

def validate_datetime_range(start_dt: datetime, end_dt: datetime, max_days: int = 365) -> tuple[bool, str]:
    """
    Валидирует диапазон дат
    
    Args:
        start_dt: Начальная дата
        end_dt: Конечная дата  
        max_days: Максимальное количество дней в диапазоне
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        start_utc = ensure_timezone_aware(start_dt)
        end_utc = ensure_timezone_aware(end_dt)
        
        if start_utc is None or end_utc is None:
            return False, "Invalid datetime objects"
            
        if start_utc > end_utc:
            return False, "Start date cannot be after end date"
            
        days_diff = days_between_utc(start_utc, end_utc)
        if days_diff > max_days:
            return False, f"Date range too large: {days_diff} days (max {max_days})"
            
        return True, ""
        
    except Exception as e:
        return False, f"Validation error: {e}"