#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для работы с Telegram Bot API.
"""

import logging
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
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
SEARCH, CHOOSE_BOOK, RECOMMEND = range(3)

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
    
    # Очищаем контекст при новом поиске
    context.user_data.clear()
    context.user_data['search_attempts'] = 0
    
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
    search_attempts = context.user_data.get('search_attempts', 0)
    
    if search_attempts >= 2:
        await update.message.reply_text(
            "К сожалению, мы не смогли найти подходящую книгу после двух попыток. "
            "Пожалуйста, уточните ваш запрос и попробуйте снова с помощью команды /search"
        )
        return ConversationHandler.END
    
    await update.message.reply_text("Ищу книгу по вашему запросу... Это может занять некоторое время.")
    
    try:
        # Сохраняем запрос пользователя в контексте
        context.user_data['last_query'] = user_query
        context.user_data['search_attempts'] = search_attempts + 1
        
        # Вызов сервиса поиска книг
        result, books_data = await search_book(user_query, context.user_data.get('excluded_books', []))
        
        if not books_data:
            await update.message.reply_text(result)
            return ConversationHandler.END
        
        # Сохраняем найденные книги в контексте
        context.user_data['found_books'] = books_data
        
        # Формируем сообщение с кнопками для выбора книги
        keyboard = []
        for i, book in enumerate(books_data, 1):
            keyboard.append([f"{i}. {book['title_ru']}"])
        keyboard.append(["🔍 Искать еще раз"])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"{result}\n\nВыберите книгу из списка или нажмите 'Искать еще раз' для продолжения поиска.",
            reply_markup=reply_markup
        )
        return CHOOSE_BOOK
        
    except Exception as e:
        logger.error(f"Ошибка при поиске книги: {e}")
        await update.message.reply_text(
            "Произошла ошибка при поиске книги. Пожалуйста, попробуйте снова позже."
        )
        return ConversationHandler.END

async def process_book_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора книги пользователем"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return ConversationHandler.END
    
    choice = update.message.text
    books_data = context.user_data.get('found_books', [])
    
    if choice == "🔍 Искать еще раз":
        # Добавляем текущие книги в исключенные
        excluded_books = context.user_data.get('excluded_books', [])
        excluded_books.extend([book['title_en'] for book in books_data])
        context.user_data['excluded_books'] = excluded_books
        
        # Возвращаемся к поиску с тем же запросом
        return await process_search(update, context)
    
    try:
        # Пытаемся получить номер выбранной книги
        book_index = int(choice.split('.')[0]) - 1
        if 0 <= book_index < len(books_data):
            selected_book = books_data[book_index]
            
            # Сохраняем выбранную книгу в контексте
            context.user_data['selected_book'] = selected_book
            
            # Убираем клавиатуру
            await update.message.reply_text(
                f"Вы выбрали книгу: {selected_book['title_ru']}\n\n"
                "Хотите получить рекомендации на основе этой книги?",
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Добавляем кнопки для выбора действия
            keyboard = [["Да, получить рекомендации"], ["Нет, спасибо"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Выберите действие:",
                reply_markup=reply_markup
            )
            return RECOMMEND
            
    except (ValueError, IndexError):
        await update.message.reply_text(
            "Пожалуйста, выберите книгу из списка или нажмите 'Искать еще раз'."
        )
        return CHOOSE_BOOK

async def process_recommendation_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора пользователя относительно получения рекомендаций"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return ConversationHandler.END
    
    choice = update.message.text
    selected_book = context.user_data.get('selected_book')
    
    if choice == "Да, получить рекомендации" and selected_book:
        await update.message.reply_text(
            "Ищу рекомендации на основе книги... Это может занять некоторое время.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        try:
            # Используем английское название для рекомендаций
            result = await recommend_books(selected_book['title_en'], 3)
            await update.message.reply_text(result)
        except Exception as e:
            logger.error(f"Ошибка при получении рекомендаций: {e}")
            await update.message.reply_text(
                "Произошла ошибка при поиске рекомендаций. Пожалуйста, попробуйте снова позже."
            )
    else:
        await update.message.reply_text(
            "Спасибо за использование бота! Если захотите найти другую книгу, используйте команду /search",
            reply_markup=ReplyKeyboardRemove()
        )
    
    return ConversationHandler.END

async def process_recommend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка запроса на рекомендацию книг"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return ConversationHandler.END
    
    user_query = update.message.text
    await update.message.reply_text("Ищу рекомендации на основе книги... Это может занять некоторое время.")
    
    try:
        # Вызов сервиса рекомендации книг
        result = await recommend_books(user_query, 3)
        await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций: {e}")
        await update.message.reply_text(
            "Произошла ошибка при поиске рекомендаций. Пожалуйста, попробуйте снова позже."
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
            CHOOSE_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_book_choice)],
            RECOMMEND: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_recommendation_choice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_recommend)
            ]
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