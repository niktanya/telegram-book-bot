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
from dotenv import load_dotenv
from rapidfuzz import process
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher
from services.database import (
    get_all_books, 
    get_all_ratings, 
    get_book_by_title,
    get_book_by_id,
    get_user_ratings
)

from models.book import Book

load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Определяем путь к данным для рекомендательной системы
DATA_DIR = Path(__file__).parent.parent.parent / "data"
RATINGS_FILE = DATA_DIR / "ratings.csv"
BOOKS_FILE = DATA_DIR / "books.csv"

async def recommend_books(book_query: str, num_recommendations: int = 3, similarity_threshold: float = 0.3) -> List[Dict[str, Any]]:
    """
    Получение рекомендаций книг на основе запроса пользователя.
    
    Args:
        book_query: Запрос пользователя (название книги или описание)
        num_recommendations: Количество рекомендаций
        similarity_threshold: Пороговое значение схожести для коллаборативной фильтрации
        
    Returns:
        Список словарей с рекомендациями
    """
    try:
        # Проверяем наличие данных в базе
        books_df = get_all_books()
        ratings_df = get_all_ratings()
        
        if not books_df.empty and not ratings_df.empty:
            return await recommend_books_collaborative(book_query, num_recommendations, similarity_threshold)
        else:
            return await recommend_books_gpt(book_query, num_recommendations)
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций: {e}")
        raise

def find_closest_book_title(query, titles, threshold=75):
    """
    Поиск наиболее похожего названия книги в датасете.
    
    Args:
        query: Запрос пользователя (название книги)
        titles: Список названий книг
        threshold: Пороговое значение схожести (по умолчанию экспертно взято значение 75)
        
    Returns:
        Название книги или None, если схожесть ниже порога
    """

    match, score, idx = process.extractOne(query, titles)
    if score >= threshold:
        return titles[idx]
    else:
        return None

async def recommend_books_collaborative(book_query: str, num_recommendations: int = 3, similarity_threshold: float = 0.3) -> List[Dict[str, Any]]:
    """
    Рекомендации книг на основе коллаборативной фильтрации.
    
    Args:
        book_query: Название книги
        num_recommendations: Количество рекомендаций
        similarity_threshold: Пороговое значение схожести (от 0 до 1)
        
    Returns:
        Список словарей с рекомендациями
    """
    try:
        # Получаем данные из базы
        books_df = get_all_books()
        ratings_df = get_all_ratings()
        
        # Ищем книгу в базе
        book = get_book_by_title(book_query)

        if not book:
            logger.info(f"Книга '{book_query}' не найдена в базе по точному или частичному совпадению.")
            # Если не найдена, пытаемся найти наиболее похожее название во всей базе
            all_books_titles = books_df['title_ru'].tolist()
            closest_title = find_closest_book_title(book_query, all_books_titles)

            if closest_title:
                logger.info(f"Найдено наиболее похожее название: '{closest_title}'.")
                book = get_book_by_title(closest_title)
                if book:
                     logger.info(f"Книга с похожим названием найдена в базе. ID: {book['book_id']}")
                else:
                     logger.error(f"Ошибка: Не удалось получить данные книги по похожему названию '{closest_title}'")
                     return await recommend_books_gpt(book_query, num_recommendations)
            else:
                 logger.info(f"Не найдено похожее название книги для запроса '{book_query}'.")
                 return await recommend_books_gpt(book_query, num_recommendations)

        if not book:
             logger.info("Книга не найдена в базе данных после всех попыток.")
             return await recommend_books_gpt(book_query, num_recommendations)

        book_id = book['book_id']
        
        # Создаем матрицу оценок
        ratings_matrix = ratings_df.pivot_table(
            index='user_id', 
            columns='book_id', 
            values='rating'
        ).fillna(0)
        
        # Вычисляем косинусное сходство между книгами
        book_similarity = cosine_similarity(ratings_matrix.T)
        book_similarity_df = pd.DataFrame(
            book_similarity,
            index=ratings_matrix.columns,
            columns=ratings_matrix.columns
        )
        
        # Получаем похожие книги
        similar_books = book_similarity_df[book_id].sort_values(ascending=False)[1:num_recommendations+1]
        
        # Фильтруем книги по порогу схожести
        filtered_books = similar_books[similar_books >= similarity_threshold]
        
        # Если нет книг, проходящих порог схожести, используем GPT
        if filtered_books.empty:
            logger.info(f"Нет книг со схожестью выше порога {similarity_threshold}. Переключаемся на GPT.")
            return await recommend_books_gpt(book_query, num_recommendations)
        
        # Формируем рекомендации только из книг, прошедших порог
        recommendations = []
        for similar_book_id, similarity in filtered_books.items():
            book_data = get_book_by_id(similar_book_id)
            if book_data:
                recommendations.append({
                    "title": book_data['title_ru'],
                    "authors": book_data['authors_ru'],
                    "year": book_data['year'],
                    "description": book_data['description'],
                    "genre": book_data['genre'],
                    "similarity": float(similarity),
                    "book_id": similar_book_id
                })
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Ошибка при коллаборативной фильтрации: {e}")
        return await recommend_books_gpt(book_query, num_recommendations)

async def recommend_books_gpt(book_query: str, num_recommendations: int = 3) -> List[Dict[str, Any]]:
    """
    Рекомендации книг с использованием OpenAI GPT API.
    
    Args:
        book_query: Название книги
        num_recommendations: Количество рекомендаций
        
    Returns:
        Список словарей с рекомендациями
    """
    try:
        # Запрос к GPT API
        logger.info(f"Отправка запроса рекомендаций к GPT API для книги: {book_query}")

        instructions = """
            Ты - книжный эксперт. Твоя задача - порекомендовать {num_recommendations} книг, похожих на книгу,
            указанную пользователем. Рекомендации должны быть основаны на схожести жанра, стиля, темы и т.д.

            Для каждой рекомендованной книги укажи (все поля должны быть на русском языке):
            - Название (на русском)
            - Автор (на русском)
            - Год издания
            - Краткое описание (до 100 слов, на русском)
            - Жанр (на русском)
            - Почему она похожа на запрошенную книгу (1-2 предложения, на русском)
            
            Ответ должен быть в формате JSON:
            {{
                "original_book": {{
                    "title": "Название исходной книги (на русском)",
                    "authors": "Авторы исходной книги (на русском) через запятую и пробел, например: <Автор_1, Автор_2>"
                }},
                "recommendations": [
                    {{
                        "title": "Название книги (на русском)",
                        "authors": "Автор книги (на русском)",
                        "year": "Год издания",
                        "description": "Краткое описание (на русском)",
                        "genre": "Жанр (на русском)",
                        "similarity": "Почему похожа на исходную книгу (на русском)"
                    }}
                ]
            }}
        """
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "developer", "content": instructions},
                {"role": "user", "content": f"Порекомендуй книги, похожие на '{book_query}'"}
            ],
            # temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        # Обработка ответа
        content = response.choices[0].message.content
        
        # Парсинг JSON
        data = json.loads(content)
        original_book = data.get("original_book", {})
        recommendations = data.get("recommendations", [])
        
        if not recommendations:
            # Возвращаем пустой список, если рекомендаций нет
            return []
        
        # Формирование ответа (теперь возвращаем список словарей)
        # result = f"На основе книги '{original_book.get('title', book_query)}' "
        # if original_book.get('authors'):
        #     result += f"авторов {original_book.get('authors')} "
        # result += "рекомендую:\n\n"
        
        processed_recommendations = []
        for i, rec_data in enumerate(recommendations, 1):
            book = Book(
                title=rec_data.get("title", "Неизвестно"),
                authors=rec_data.get("authors", "Неизвестно"),
                year=rec_data.get("year", "Неизвестно"),
                description=rec_data.get("description", "Описание отсутствует"),
                genre=rec_data.get("genre", "Неизвестно")
            )
            # Попытка найти книгу в базе по названию и добавить book_id
            book_in_db = get_book_by_title(book.title)
            if book_in_db:
                rec_data['book_id'] = book_in_db['book_id']

            # Добавляем обработанные данные книги в список
            processed_recommendations.append({
                "title": book.title,
                "authors": book.authors,
                "year": book.year,
                "description": book.description,
                "genre": book.genre,
                "similarity": rec_data.get("similarity", "Неизвестно"), # GPT может вернуть текстовое объяснение
                "book_id": rec_data.get('book_id') # book_id может отсутствовать
            })

        return processed_recommendations
    
    except Exception as e:
        logger.error(f"Ошибка при запросе рекомендаций к GPT API: {e}")
        raise Exception(f"Ошибка при получении рекомендаций: {e}") 