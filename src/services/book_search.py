#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для поиска книг с использованием OpenAI GPT API.
"""

import os
import logging
import json
from openai import AsyncOpenAI

from models.book import Book

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def search_book(query: str) -> str:
    """
    Поиск книги по запросу пользователя через OpenAI GPT API.
    
    Args:
        query: Запрос пользователя (описание, автор или название книги)
        
    Returns:
        Строка с результатом поиска
    """
    try:
        # Запрос к GPT API
        logger.info(f"Отправка запроса к GPT API: {query}")
        
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """
                Ты - книжный эксперт. Твоя задача - найти книгу по запросу пользователя.
                Запрос может содержать описание сюжета, автора, название или их комбинацию.
                Если есть несколько возможных вариантов, предложи до 3 наиболее подходящих книг.
                Для каждой книги укажи:
                - Название
                - Автор
                - Год издания
                - Краткое описание (до 100 слов)
                - Жанр
                
                Ответ должен быть в формате JSON:
                {
                    "books": [
                        {
                            "title": "Название книги",
                            "author": "Автор книги",
                            "year": "Год издания",
                            "description": "Краткое описание",
                            "genre": "Жанр"
                        }
                    ]
                }
                """},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        # Обработка ответа
        content = response.choices[0].message.content
        
        # Парсинг JSON
        data = json.loads(content)
        books = data.get("books", [])
        
        if not books:
            return "К сожалению, не удалось найти книгу по вашему запросу. Попробуйте уточнить запрос."
        
        # Формирование ответа
        result = "Вот что я нашел по вашему запросу:\n\n"
        for i, book_data in enumerate(books, 1):
            book = Book(
                title=book_data.get("title", "Неизвестно"),
                author=book_data.get("author", "Неизвестно"),
                year=book_data.get("year", "Неизвестно"),
                description=book_data.get("description", "Описание отсутствует"),
                genre=book_data.get("genre", "Неизвестно")
            )
            result += f"{i}. 📚 {book.to_string()}\n\n"
        
        return result
    
    except Exception as e:
        logger.error(f"Ошибка при запросе к GPT API: {e}")
        raise Exception(f"Ошибка при поиске книги: {e}") 