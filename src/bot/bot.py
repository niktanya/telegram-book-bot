#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для работы с Telegram Bot API.
"""

import logging
import os
import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)

from services.book_search import search_book
from services.recommendation import recommend_books
from services.database import add_book, add_rating, get_book_rating, get_user_ratings

# Состояния для конверсации
SEARCH, CHOOSE_BOOK, RECOMMEND_FROM_RATE, RECOMMEND_DIRECT, RATE, CHOOSE_RATING = range(6)

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
        "/rate - Оценить книгу (поиск + оценка)\n"
        "/myratings - Посмотреть ваши оценки книг\n"
        "/help - Получить справку о работе бота"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return
    
    await update.message.reply_text(
        "Я могу помочь вам найти книги, получить рекомендации и оценить прочитанные книги.\n\n"
        "Доступные команды:\n"
        "/search - Найти книгу по описанию, автору или названию\n"
        "/recommend - Получить рекомендации на основе книги\n"
        "/rate - Оценить книгу (поиск + оценка)\n"
        "/myratings - Посмотреть ваши оценки книг\n"
        "/cancel - Отменить текущую операцию\n\n"
        "Как это работает:\n"
        "1. Используйте /search или /rate для поиска книги\n"
        "2. Выберите книгу из списка результатов\n"
        "3. При оценке книги (/rate) вы можете:\n"
        "   - Поставить оценку от 1 до 5 звезд\n"
        "   - Получить рекомендации на основе книги\n"
        "4. Используйте /myratings чтобы посмотреть все ваши оценки"
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
            
            # Добавляем книгу в базу данных, если её там нет
            book_id = add_book(selected_book)
            context.user_data['selected_book_id'] = book_id
            
            # Убираем клавиатуру
            await update.message.reply_text(
                f"Вы выбрали книгу: {selected_book['title_ru']}\n\n",
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Проверяем режим работы
            if context.user_data.get('mode') == 'rate':
                # Проверяем, есть ли уже оценка
                user_id = update.effective_user.id
                existing_rating = get_book_rating(book_id, user_id)
                
                # Создаем inline клавиатуру для оценки
                keyboard = []
                for i in range(1, 6):
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{i} {'⭐' * i}",
                            callback_data=f"rate_{i}"
                        )
                    ])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if existing_rating:
                    await update.message.reply_text(
                        f"У вас уже есть оценка для этой книги: {existing_rating} {'⭐' * existing_rating}\n"
                        "Выберите новую оценку:",
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_text(
                        "Оцените книгу от 1 до 5 звезд:",
                        reply_markup=reply_markup
                    )
                return RATE
            else:
                # Добавляем кнопки для выбора действия
                keyboard = [["Да, получить рекомендации"], ["Нет, спасибо"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                await update.message.reply_text(
                    "Хотите получить рекомендации на основе этой книги?",
                    reply_markup=reply_markup
                )
                return RECOMMEND_FROM_RATE
            
    except (ValueError, IndexError):
        await update.message.reply_text(
            "Пожалуйста, выберите книгу из списка или нажмите 'Искать еще раз'."
        )
        return CHOOSE_BOOK

async def process_recommendation_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора пользователя относительно получения рекомендаций после оценки"""
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
    """
    Обработка запроса на рекомендации книг.
    """
    try:
        user_id = update.effective_user.id
        if user_id not in ALLOWED_USERS:
            await update.message.reply_text("Извините, у вас нет доступа к боту.")
            return ConversationHandler.END

        book_query = update.message.text.strip()
        if not book_query:
            await update.message.reply_text("Пожалуйста, введите название книги или описание.")
            return RECOMMEND_DIRECT

        # Получаем рекомендации
        recommendations_json = await recommend_books(book_query)
        recommendations = json.loads(recommendations_json)

        if not recommendations:
            await update.message.reply_text(
                "К сожалению, не удалось найти подходящие рекомендации. "
                "Попробуйте изменить запрос или использовать поиск книг через /search."
            )
            return ConversationHandler.END

        # Формируем сообщение с рекомендациями
        message = "📚 Вот книги, которые могут вам понравиться:\n\n"
        
        for i, book in enumerate(recommendations, 1):
            similarity = book.get('similarity', 0)
            message += (
                f"{i}. <b>{book['title']}</b>\n"
                f"👤 Авторы: {book['authors']}\n"
                f"📅 Год: {book['year']}\n"
                f"📖 Описание: {book['description']}\n"
                f"🏷 Жанр: {book['genre']}\n"
            )
            if similarity > 0:
                message += f"📊 Схожесть: {similarity:.2f}\n"
            message += "\n"

        # Добавляем кнопки для оценки книг
        keyboard = []
        for i in range(len(recommendations)):
            keyboard.append([
                InlineKeyboardButton(f"Оценить книгу {i+1}", callback_data=f"rate_{i}")
            ])
        keyboard.append([InlineKeyboardButton("Искать еще раз", callback_data="search_again")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        # Сохраняем рекомендации в контексте
        context.user_data['current_recommendations'] = recommendations
        
        return RECOMMEND_CHOICE

    except Exception as e:
        logger.error(f"Ошибка при обработке рекомендаций: {e}")
        await update.message.reply_text(
            "Произошла ошибка при получении рекомендаций. "
            "Пожалуйста, попробуйте позже или используйте поиск книг через /search."
        )
        return ConversationHandler.END

async def rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /rate"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return ConversationHandler.END
    
    # Очищаем контекст при новом поиске
    context.user_data.clear()
    context.user_data['search_attempts'] = 0
    context.user_data['mode'] = 'rate'  # Указываем, что это режим оценки
    
    await update.message.reply_text(
        "Пожалуйста, введите описание, автора или название книги, которую хотите оценить."
    )
    return SEARCH

async def process_rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора оценки через inline кнопки"""
    query = update.callback_query
    await query.answer()  # Отвечаем на callback, чтобы убрать часики с кнопки
    
    if not await check_user(update):
        await query.message.reply_text("У вас нет доступа к этому боту.")
        return ConversationHandler.END
    
    try:
        rating = int(query.data.split('_')[1])
        if 1 <= rating <= 5:
            book_id = context.user_data.get('selected_book_id')
            user_id = query.from_user.id
            
            # Сохраняем оценку
            add_rating(book_id, user_id, rating)
            
            # Обновляем сообщение с оценкой
            await query.message.edit_text(
                f"Спасибо за оценку! Вы поставили книге {rating} {'⭐' * rating}"
            )
            
            # Предлагаем получить рекомендации
            keyboard = [["Да, получить рекомендации"], ["Нет, спасибо"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await query.message.reply_text(
                "Хотите получить рекомендации на основе этой книги?",
                reply_markup=reply_markup
            )
            return RECOMMEND_FROM_RATE
            
    except (ValueError, IndexError):
        await query.message.reply_text(
            "Произошла ошибка при обработке оценки. Пожалуйста, попробуйте снова."
        )
        return ConversationHandler.END

async def my_ratings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /myratings"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return
    
    user_id = update.effective_user.id
    ratings = get_user_ratings(user_id)
    
    if not ratings:
        await update.message.reply_text(
            "У вас пока нет оцененных книг. Используйте команду /rate для оценки книг."
        )
        return
    
    # Формируем сообщение со списком оценок
    result = "Ваши оценки книг:\n\n"
    for rating_data in ratings:
        result += (
            f"📚 *{rating_data['title_ru']}*\n"
            f"Авторы: {rating_data['authors_ru']}\n"
            f"Ваша оценка: {rating_data['rating']} {'⭐' * rating_data['rating']}\n"
            f"Жанр: {rating_data['genre']}\n\n"
        )
    
    await update.message.reply_text(result)

async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /recommend"""
    if not await check_user(update):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Пожалуйста, введите название книги, на основе которой вы хотите получить рекомендации."
    )
    return RECOMMEND_DIRECT

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
            CommandHandler("recommend", recommend_command),
            CommandHandler("rate", rate_command)
        ],
        states={
            SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_search)],
            CHOOSE_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_book_choice)],
            RECOMMEND_FROM_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_recommendation_choice)],
            RECOMMEND_DIRECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_recommend)],
            RATE: [CallbackQueryHandler(process_rating_callback, pattern=r"^rate_\d+$")]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("myratings", my_ratings_command))
    application.add_handler(conv_handler)
    
    # Запуск бота
    if CHECK_USERS:
        logger.info(f"Бот запущен в режиме проверки доступа. Разрешенные пользователи: {allowed_user_ids}")
    else:
        logger.info("Бот запущен без проверки доступа")
    
    application.run_polling() 