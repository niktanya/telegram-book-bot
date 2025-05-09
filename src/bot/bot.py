#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для работы с Telegram Bot API.
"""

import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

from services.book_search import search_book
from services.recommendation import recommend_books

# Состояния для конверсации
SEARCH, RECOMMEND = range(2)

# Настройка логирования
logger = logging.getLogger(__name__)

# Получаем список разрешенных пользователей из переменных окружения
# Формат: "123456789,987654321"
ALLOWED_USERS = os.getenv("ALLOWED_USERS", "")
allowed_user_ids = [int(user_id.strip()) for user_id in ALLOWED_USERS.split(",") if user_id.strip()] if ALLOWED_USERS else []

# Флаг, указывающий, нужно ли проверять пользователей
CHECK_USERS = bool(allowed_user_ids) and os.getenv("ENVIRONMENT") == "production"

async def check_user(update: Update) -> bool:
    """
    Проверяет, имеет ли пользователь доступ к боту.
    
    Args:
        update: Объект обновления Telegram
        
    Returns:
        True, если пользователь имеет доступ, иначе False
    """
    if not CHECK_USERS:
        return True
    
    user_id = update.effective_user.id
    return user_id in allowed_user_ids

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return
    
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот для поиска и рекомендации книг.\n\n"
        "Доступные команды:\n"
        "/search - Найти книгу по описанию, автору или названию\n"
        "/recommend - Получить рекомендации на основе книги\n"
        "/help - Получить справку о работе бота"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return
    
    await update.message.reply_text(
        "Я могу помочь вам найти книги и получить рекомендации.\n\n"
        "Доступные команды:\n"
        "/search - Найти книгу по описанию, автору или названию\n"
        "/recommend - Получить рекомендации на основе книги\n"
        "/cancel - Отменить текущую операцию"
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /search"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Пожалуйста, введите описание, автора или название книги, которую хотите найти."
    )
    return SEARCH

async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка запроса на поиск книги"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return ConversationHandler.END
    
    user_query = update.message.text
    await update.message.reply_text("Ищу книгу по вашему запросу... Это может занять некоторое время.")
    
    try:
        # Вызов сервиса поиска книг
        result = await search_book(user_query)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Ошибка при поиске книги: {e}")
        await update.message.reply_text(
            "Произошла ошибка при поиске книги. Пожалуйста, попробуйте снова позже."
        )
    
    return ConversationHandler.END

async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /recommend"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Пожалуйста, введите название книги, на основе которой вы хотите получить рекомендации."
    )
    return RECOMMEND

async def process_recommend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка запроса на рекомендацию книг"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return ConversationHandler.END
    
    user_query = update.message.text
    await update.message.reply_text("Ищу рекомендации на основе книги... Это может занять некоторое время.")
    
    try:
        # Вызов сервиса рекомендации книг
        # По умолчанию рекомендуем 5 книг
        result = await recommend_books(user_query, 5)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций: {e}")
        await update.message.reply_text(
            "Произошла ошибка при поиске рекомендаций. Пожалуйста, попробуйте снова позже."
        )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /cancel"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return ConversationHandler.END
    
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

def run_bot(token: str) -> None:
    """Функция для запуска бота"""
    # Создание приложения
    application = Application.builder().token(token).build()
    
    # Создание обработчика диалога
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("search", search_command),
            CommandHandler("recommend", recommend_command)
        ],
        states={
            SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_search)],
            RECOMMEND: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_recommend)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)
    
    # Запуск бота
    if CHECK_USERS:
        logger.info(f"Бот запущен в режиме проверки доступа. Разрешенные пользователи: {allowed_user_ids}")
    else:
        logger.info("Бот запущен без проверки доступа")
    
    application.run_polling() 