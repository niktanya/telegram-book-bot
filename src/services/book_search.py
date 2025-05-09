#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для поиска книг с использованием OpenAI GPT API.
"""

import os
import logging
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI

from models.book import Book

# Настройка логирования
logger = logging.getLogger(__name__)

async def search_book(query: str) -> str:
    """
    Поиск книги по запросу пользователя через OpenAI GPT API.
    
    Args:
        query: Запрос пользователя (описание, автор или название книги)
        
    Returns:
        Строка с результатом поиска
    """
    try:
        # Загружаем переменные окружения (можно оставить, если вдруг вызывается отдельно)
        load_dotenv()
        # Инициализируем клиента внутри функции
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        logger.info(os.getenv("OPENAI_API_KEY"))

        # Запрос к GPT API
        logger.info(f"Отправка запроса к GPT API: {query}")

        instructions = """
            Ты — книжный эксперт. Твоя задача — найти книгу по запросу пользователя.
            Запрос может содержать описание сюжета, автора, название или их комбинацию.
            Если есть несколько возможных вариантов, предложи до 3 наиболее подходящих книг.

            Для каждой книги укажи:
            - Название на русском языке (title_ru)
            - Название на английском языке (title_en)
            - Авторы на русском языке, через запятую и пробел, например "Автор_1, Автор_2" (authors_ru)
            - Авторы на английском языке, через запятую и пробел (authors_en)
            - Год издания (year)
            - Краткое описание на русском языке (description)
            - Жанр на русском языке (genre)

            Ответ должен быть в формате JSON:
            {
                "books": [
                    {
                        "title_ru": "Название книги на русском",
                        "title_en": "Название книги на английском",
                        "authors_ru": "Авторы на русском",
                        "authors_en": "Авторы на английском",
                        "year": "Год издания",
                        "description": "Краткое описание на русском",
                        "genre": "Жанр на русском"
                    }
                ]
            }
        """
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "developer", "content": instructions},
                {"role": "user", "content": query}
            ],
            # temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        # Обработка ответа
        content = response.choices[0].message.content
        
        # Парсинг JSON
        data = json.loads(content)
        books = data.get("books", [])
        
        if not books:
            return "К сожалению, не удалось найти книгу по вашему запросу. Попробуйте уточнить запрос."
        
        # Формирование ответа для пользователя
        result = "Вот что я нашел по вашему запросу:\n\n"
        for i, book_data in enumerate(books, 1):
            result += (
                f"{i}. 📚 *{book_data.get('title_ru', 'Неизвестно')}* (на англ.: {book_data.get('title_en', 'Unknown')})\n"
                f"Авторы: {book_data.get('authors_ru', 'Неизвестно')} (на англ.: {book_data.get('authors_en', 'Unknown')})\n"
                f"Год: {book_data.get('year', 'Неизвестно')}\n"
                f"Жанр: {book_data.get('genre', 'Неизвестно')}\n"
                f"Описание: {book_data.get('description', 'Описание отсутствует')}\n\n"
            )
        return result
    
    except Exception as e:
        logger.error(f"Ошибка при запросе к GPT API: {e}")
        raise Exception(f"Ошибка при поиске книги: {e}") 