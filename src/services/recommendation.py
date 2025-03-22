#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для рекомендации книг на основе введенной пользователем книги.
Включает два метода: 
1. На основе коллаборативной фильтрации с использованием датасета оценок книг
2. С использованием OpenAI GPT API
"""

import os
import logging
import json
import pandas as pd
import numpy as np
from pathlib import Path
from openai import AsyncOpenAI

from models.book import Book

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Определяем путь к данным для рекомендательной системы
DATA_DIR = Path(__file__).parent.parent.parent / "data"
RATINGS_FILE = DATA_DIR / "book_ratings.csv"
BOOKS_FILE = DATA_DIR / "books.csv"

async def recommend_books(book_query: str, num_recommendations: int = 5) -> str:
    """
    Получение рекомендаций книг на основе запроса пользователя.
    В зависимости от наличия данных для коллаборативной фильтрации,
    использует либо датасет оценок, либо OpenAI GPT API.
    
    Args:
        book_query: Запрос пользователя (название книги)
        num_recommendations: Количество рекомендаций
        
    Returns:
        Строка с результатом рекомендаций
    """
    try:
        # Проверяем наличие данных для коллаборативной фильтрации
        if RATINGS_FILE.exists() and BOOKS_FILE.exists():
            return await recommend_books_collaborative(book_query, num_recommendations)
        else:
            # Если данных нет, используем GPT API
            return await recommend_books_gpt(book_query, num_recommendations)
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций: {e}")
        raise Exception(f"Ошибка при получении рекомендаций: {e}")

async def recommend_books_collaborative(book_query: str, num_recommendations: int = 5) -> str:
    """
    Рекомендации книг на основе коллаборативной фильтрации.
    
    Args:
        book_query: Название книги
        num_recommendations: Количество рекомендаций
        
    Returns:
        Строка с результатом рекомендаций
    """
    try:
        # Загрузка данных
        books_df = pd.read_csv(BOOKS_FILE)
        ratings_df = pd.read_csv(RATINGS_FILE)
        
        # Поиск книги в датасете
        book_matches = books_df[books_df['title'].str.contains(book_query, case=False)]
        
        if book_matches.empty:
            # Если книга не найдена в датасете, используем GPT API
            return await recommend_books_gpt(book_query, num_recommendations)
        
        # Берем первую найденную книгу
        book_id = book_matches.iloc[0]['book_id']
        
        # Получаем пользователей, которые оценили эту книгу
        users_who_read = ratings_df[ratings_df['book_id'] == book_id]['user_id'].unique()
        
        # Если мало оценок, используем GPT API
        if len(users_who_read) < 5:
            return await recommend_books_gpt(book_query, num_recommendations)
        
        # Получаем другие книги, которые читали эти пользователи
        other_books = ratings_df[ratings_df['user_id'].isin(users_who_read) & 
                             (ratings_df['book_id'] != book_id)]
        
        # Группируем по книгам и считаем среднюю оценку и количество оценок
        book_stats = other_books.groupby('book_id').agg({
            'rating': ['mean', 'count']
        }).reset_index()
        book_stats.columns = ['book_id', 'avg_rating', 'rating_count']
        
        # Фильтруем по минимальному количеству оценок
        min_ratings = 3
        filtered_books = book_stats[book_stats['rating_count'] >= min_ratings]
        
        # Сортируем по средней оценке
        recommended_books = filtered_books.sort_values('avg_rating', ascending=False).head(num_recommendations)
        
        # Объединяем с информацией о книгах
        result_df = pd.merge(recommended_books, books_df, on='book_id')
        
        # Формируем ответ
        result = f"На основе книги '{book_matches.iloc[0]['title']}' рекомендую:\n\n"
        
        for i, (_, row) in enumerate(result_df.iterrows(), 1):
            book = Book(
                title=row['title'],
                author=row.get('author', 'Неизвестно'),
                year=row.get('year', 'Неизвестно'),
                description=row.get('description', 'Описание отсутствует'),
                genre=row.get('genre', 'Неизвестно')
            )
            result += f"{i}. 📚 {book.to_string()}\nСредняя оценка: {row['avg_rating']:.2f} (на основе {row['rating_count']} оценок)\n\n"
        
        return result
    
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций через коллаборативную фильтрацию: {e}")
        # В случае ошибки используем GPT API
        return await recommend_books_gpt(book_query, num_recommendations)

async def recommend_books_gpt(book_query: str, num_recommendations: int = 5) -> str:
    """
    Рекомендации книг с использованием OpenAI GPT API.
    
    Args:
        book_query: Название книги
        num_recommendations: Количество рекомендаций
        
    Returns:
        Строка с результатом рекомендаций
    """
    try:
        # Запрос к GPT API
        logger.info(f"Отправка запроса рекомендаций к GPT API для книги: {book_query}")
        
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"""
                Ты - книжный эксперт. Твоя задача - порекомендовать {num_recommendations} книг, похожих на книгу,
                указанную пользователем. Рекомендации должны быть основаны на схожести жанра, стиля, темы и т.д.
                
                Для каждой рекомендованной книги укажи:
                - Название
                - Автор
                - Год издания
                - Краткое описание (до 100 слов)
                - Жанр
                - Почему она похожа на запрошенную книгу (1-2 предложения)
                
                Ответ должен быть в формате JSON:
                {{
                    "original_book": {{
                        "title": "Название исходной книги",
                        "author": "Автор исходной книги"
                    }},
                    "recommendations": [
                        {{
                            "title": "Название книги",
                            "author": "Автор книги",
                            "year": "Год издания",
                            "description": "Краткое описание",
                            "genre": "Жанр",
                            "similarity": "Почему похожа на исходную книгу"
                        }}
                    ]
                }}
                """},
                {"role": "user", "content": f"Порекомендуй книги, похожие на '{book_query}'"}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        # Обработка ответа
        content = response.choices[0].message.content
        
        # Парсинг JSON
        data = json.loads(content)
        original_book = data.get("original_book", {})
        recommendations = data.get("recommendations", [])
        
        if not recommendations:
            return "К сожалению, не удалось найти рекомендации для указанной книги. Попробуйте ввести более известную книгу."
        
        # Формирование ответа
        result = f"На основе книги '{original_book.get('title', book_query)}' "
        if original_book.get('author'):
            result += f"автора {original_book.get('author')} "
        result += "рекомендую:\n\n"
        
        for i, rec_data in enumerate(recommendations, 1):
            book = Book(
                title=rec_data.get("title", "Неизвестно"),
                author=rec_data.get("author", "Неизвестно"),
                year=rec_data.get("year", "Неизвестно"),
                description=rec_data.get("description", "Описание отсутствует"),
                genre=rec_data.get("genre", "Неизвестно")
            )
            result += f"{i}. 📚 {book.to_string()}\n"
            if rec_data.get("similarity"):
                result += f"Почему похожа: {rec_data.get('similarity')}\n"
            result += "\n"
        
        return result
    
    except Exception as e:
        logger.error(f"Ошибка при запросе рекомендаций к GPT API: {e}")
        raise Exception(f"Ошибка при получении рекомендаций: {e}") 