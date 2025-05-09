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

from models.book import Book

load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Определяем путь к данным для рекомендательной системы
DATA_DIR = Path(__file__).parent.parent.parent / "data"
RATINGS_FILE = DATA_DIR / "book_ratings.csv"
BOOKS_FILE = DATA_DIR / "books.csv"

async def recommend_books(book_query: str, num_recommendations: int = 3) -> str:
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

async def recommend_books_collaborative(book_query: str, num_recommendations: int = 3) -> str:
    """
    Рекомендации книг на основе коллаборативной фильтрации.
    
    Args:
        book_query: Название книги
        num_recommendations: Количество рекомендаций
        
    Returns:
        Строка с результатом рекомендаций
    """

    title_name_in_dataset = 'original_title'

    try:
        # Загрузка данных
        books_df = pd.read_csv(BOOKS_FILE)
        ratings_df = pd.read_csv(RATINGS_FILE)

        # Сначала пробуем прямое вхождение
        book_matches = books_df[books_df[title_name_in_dataset].str.contains(book_query, case=False)]

        # Если не найдено, ищем по схожести
        if book_matches.empty:
            closest_title = find_closest_book_title(book_query, books_df[title_name_in_dataset].tolist())
            if closest_title:
                book_matches = books_df[books_df[title_name_in_dataset] == closest_title]

        if book_matches.empty:
            return await recommend_books_gpt(book_query, num_recommendations)

        book_id = book_matches.iloc[0]['book_id']

        ratings_matrix = ratings_df.pivot_table(index='user_id', columns='book_id', values='rating').fillna(0)
        book_vectors = ratings_matrix.T

        if book_id not in book_vectors.index:
            return await recommend_books_gpt(book_query, num_recommendations)

        target_vector = book_vectors.loc[[book_id]]
        similarities = cosine_similarity(target_vector, book_vectors)[0]

        similarities_df = pd.DataFrame({
            'book_id': book_vectors.index,
            'similarity': similarities
        }).sort_values('similarity', ascending=False)

        similarities_df = similarities_df[similarities_df['book_id'] != book_id]
        top_books = similarities_df.head(num_recommendations)

        recommended_books = books_df[books_df['book_id'].isin(top_books['book_id'])]
        result_df = pd.merge(recommended_books, top_books, on='book_id')

        result = f"На основе книги '{book_matches.iloc[0]['title']}' рекомендую (обратите внимание, названия на английском — попробуйте найти русский перевод по названию и автору через поисковик):\n\n"

        for i, (_, row) in enumerate(result_df.iterrows(), 1):
            book = Book(
                title=row['title'],
                authors=row.get('authors', 'Неизвестно'),
                year=row.get('year', 'Неизвестно'),
                description=row.get('description', 'Описание отсутствует'),
                genre=row.get('genre', 'Неизвестно')
            )
            result += f"{i}. 📚 {book.to_string()}\nКоэффициент схожести на основе оценок других пользователей: {row['similarity']:.2f}\n\n"

        return result

    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций через коллаборативную фильтрацию: {e}")
        return await recommend_books_gpt(book_query, num_recommendations)

async def recommend_books_gpt(book_query: str, num_recommendations: int = 3) -> str:
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

        instructions = """
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
                    "authors": "Авторы исходной книги через запятую и пробел, например: <Автор_1, Автор_2>"
                }},
                "recommendations": [
                    {{
                        "title": "Название книги",
                        "authors": "Автор книги",
                        "year": "Год издания",
                        "description": "Краткое описание",
                        "genre": "Жанр",
                        "similarity": "Почему похожа на исходную книгу"
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
            return "К сожалению, не удалось найти рекомендации для указанной книги. Попробуйте ввести более известную книгу."
        
        # Формирование ответа
        result = f"На основе книги '{original_book.get('title', book_query)}' "
        if original_book.get('authors'):
            result += f"авторов {original_book.get('authors')} "
        result += "рекомендую:\n\n"
        
        for i, rec_data in enumerate(recommendations, 1):
            book = Book(
                title=rec_data.get("title", "Неизвестно"),
                authors=rec_data.get("authors", "Неизвестно"),
                year=rec_data.get("year", "Неизвестно"),
                description=rec_data.get("description", "Описание отсутствует"),
                genre=rec_data.get("genre", "Неизвестно")
            )
            result += f"{i}. 📚 {book.to_string()}\n"
            if rec_data.get("similarity"):
                result += f"Чем похоже на книгу из запроса: {rec_data.get('similarity')}\n"
            result += "\n"
        
        return result
    
    except Exception as e:
        logger.error(f"Ошибка при запросе рекомендаций к GPT API: {e}")
        raise Exception(f"Ошибка при получении рекомендаций: {e}") 