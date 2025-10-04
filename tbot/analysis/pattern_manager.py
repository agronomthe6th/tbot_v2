"""
Pattern Manager - управление паттернами парсинга из БД
"""
import re
import logging
from typing import Dict, List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

class PatternManager:
    """Менеджер паттернов парсинга с кешированием"""
    
    def __init__(self, db_manager):
        """
        Args:
            db_manager: Database instance
        """
        self.db = db_manager
        self._cache = {}
        self._cache_loaded = False
        
        logger.info("PatternManager initialized")
    
    def reload_patterns(self) -> None:
        """Перезагрузить паттерны из БД (очистить кеш)"""
        self._cache.clear()
        self._cache_loaded = False
        logger.info("Pattern cache cleared, will reload on next access")
    
    def _load_all_patterns(self) -> None:
        """Загрузить все активные паттерны из БД в кеш"""
        if self._cache_loaded:
            return
        
        try:
            all_patterns = self.db.get_all_patterns(active_only=True)
            
            for pattern_data in all_patterns:
                category = pattern_data['category']
                if category not in self._cache:
                    self._cache[category] = []
                
                self._cache[category].append({
                    'id': pattern_data['id'],
                    'name': pattern_data['name'],
                    'pattern': pattern_data['pattern'],
                    'priority': pattern_data['priority']
                })
            
            for category in self._cache:
                self._cache[category].sort(key=lambda x: x['priority'], reverse=True)
            
            self._cache_loaded = True
            logger.info(f"Loaded {len(all_patterns)} patterns into cache")
            
        except Exception as e:
            logger.error(f"Failed to load patterns from DB: {e}")
            self._cache_loaded = False
    
    def get_patterns(self, category: str) -> List[str]:
        """
        Получить список паттернов для категории
        
        Args:
            category: категория паттернов
            
        Returns:
            List[str]: список regex паттернов
        """
        self._load_all_patterns()
        
        patterns = self._cache.get(category, [])
        return [p['pattern'] for p in patterns]
    
    def get_patterns_by_categories(self, categories: List[str]) -> Dict[str, List[str]]:
        """
        Получить паттерны для нескольких категорий
        
        Args:
            categories: список категорий
            
        Returns:
            Dict: словарь {категория: [паттерны]}
        """
        self._load_all_patterns()
        
        result = {}
        for category in categories:
            result[category] = self.get_patterns(category)
        
        return result
    
    def test_pattern(self, pattern: str, text: str) -> List[Dict]:
        """
        Тестировать паттерн на тексте
        
        Args:
            pattern: regex паттерн
            text: текст для тестирования
            
        Returns:
            List[Dict]: список совпадений
        """
        try:
            matches = []
            for match_obj in re.finditer(pattern, text, re.IGNORECASE):
                matches.append({
                    'match': match_obj.group(),
                    'start': match_obj.start(),
                    'end': match_obj.end(),
                    'groups': match_obj.groups()
                })
            return matches
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            return []
    
    def get_cache_stats(self) -> Dict:
        """Получить статистику кеша"""
        return {
            'cache_loaded': self._cache_loaded,
            'categories_count': len(self._cache),
            'total_patterns': sum(len(patterns) for patterns in self._cache.values()),
            'categories': {
                cat: len(patterns) 
                for cat, patterns in self._cache.items()
            }
        }