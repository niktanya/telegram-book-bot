#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Главный файл для запуска Telegram-бота для поиска и рекомендации книг.
"""

import logging
import sys
import os
from dotenv import load_dotenv

from bot.bot import run_bot

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция для запуска бота"""
    # Загрузка переменных окружения
    load_dotenv()
    
    # Проверка наличия токена
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        logger.error("Токен Telegram бота не найден в переменных окружения")
        sys.exit(1)
    
    # Проверка наличия OpenAI API ключа
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OpenAI API ключ не найден в переменных окружения")
        sys.exit(1)
    
    # Запуск бота
    run_bot(telegram_token)

if __name__ == "__main__":
    main() 