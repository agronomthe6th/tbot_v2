import os

def get_channels_from_env():
    """Читаем каналы из .env"""
    channels = []
    
    target_channel = os.getenv("target_channel_id")
    if target_channel:
        channels.append({
            "id": int(target_channel),
            "name": "Main Trading Channel",
            "enabled": True
        })
    
    test_channel = os.getenv("test_channel_id")
    if test_channel:
        channels.append({
            "id": int(test_channel),
            "name": "Test Channel",
            "enabled": False
        })
    
    return channels

CHANNELS = get_channels_from_env()

SCRAPER_CONFIG = {
    "check_interval_seconds": 60,
    "initial_history_limit": 100,
}