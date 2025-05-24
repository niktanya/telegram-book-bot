#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для работы с SQLite базой данных.
"""

import os
import logging
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

# Настройка логирования
logger = logging.getLogger(__name__)

# Определяем путь к базе данных
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_FILE = DB_DIR / "books.db"

# Определяем пути к CSV файлам
BOOKS_FILE = DB_DIR / "books.csv"
RATINGS_FILE = DB_DIR / "ratings.csv"

def init_db() -> None:
    """Инициализация базы данных"""
    try:
        # Создаем директорию, если её нет
        DB_DIR.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Создаем таблицу книг
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title_en TEXT NOT NULL,
                    title_ru TEXT NOT NULL,
                    authors_en TEXT NOT NULL,
                    authors_ru TEXT NOT NULL,
                    year TEXT,
                    description TEXT,
                    genre TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Создаем таблицу оценок
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ratings (
                    rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (book_id) REFERENCES books (book_id),
                    UNIQUE(book_id, user_id)
                )
            """)
            
            conn.commit()
            logger.info("База данных успешно инициализирована")
            
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise

def add_book(book_data: Dict[str, Any]) -> int:
    """
    Добавление книги в базу данных.
    
    Args:
        book_data: Словарь с данными книги
        
    Returns:
        ID добавленной книги
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Проверяем, существует ли уже такая книга
            cursor.execute("""
                SELECT book_id FROM books 
                WHERE title_en = ? AND authors_en = ?
            """, (book_data['title_en'], book_data['authors_en']))
            
            existing_book = cursor.fetchone()
            if existing_book:
                return existing_book[0]
            
            # Добавляем новую книгу
            cursor.execute("""
                INSERT INTO books (
                    title_en, title_ru, authors_en, authors_ru,
                    year, description, genre
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                book_data['title_en'],
                book_data['title_ru'],
                book_data['authors_en'],
                book_data['authors_ru'],
                book_data.get('year'),
                book_data.get('description'),
                book_data.get('genre')
            ))
            
            conn.commit()
            return cursor.lastrowid
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении книги в базу данных: {e}")
        raise

def add_rating(book_id: int, user_id: int, rating: int) -> None:
    """
    Добавление или обновление оценки книги.
    
    Args:
        book_id: ID книги
        user_id: ID пользователя
        rating: Оценка (от 1 до 5)
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Используем INSERT OR REPLACE для обновления существующей оценки
            cursor.execute("""
                INSERT OR REPLACE INTO ratings (book_id, user_id, rating)
                VALUES (?, ?, ?)
            """, (book_id, user_id, rating))
            
            conn.commit()
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении оценки в базу данных: {e}")
        raise

def get_book_rating(book_id: int, user_id: int) -> Optional[int]:
    """
    Получение оценки книги пользователем.
    
    Args:
        book_id: ID книги
        user_id: ID пользователя
        
    Returns:
        Оценка книги или None, если оценка не найдена
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT rating FROM ratings
                WHERE book_id = ? AND user_id = ?
            """, (book_id, user_id))
            
            result = cursor.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        logger.error(f"Ошибка при получении оценки из базы данных: {e}")
        raise

def get_book_by_id(book_id: int) -> Optional[Dict[str, Any]]:
    """
    Получение информации о книге по ID.
    
    Args:
        book_id: ID книги
        
    Returns:
        Словарь с данными книги или None, если книга не найдена
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM books WHERE book_id = ?
            """, (book_id,))
            
            columns = [description[0] for description in cursor.description]
            book = cursor.fetchone()
            
            if book:
                return dict(zip(columns, book))
            return None
            
    except Exception as e:
        logger.error(f"Ошибка при получении книги из базы данных: {e}")
        raise

def get_user_ratings(user_id: int) -> List[Dict[str, Any]]:
    """
    Получение всех оценок пользователя.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Список словарей с данными об оценках и книгах
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT r.rating, b.* 
                FROM ratings r
                JOIN books b ON r.book_id = b.book_id
                WHERE r.user_id = ?
                ORDER BY r.created_at DESC
            """, (user_id,))
            
            columns = [description[0] for description in cursor.description]
            ratings = []
            
            for row in cursor.fetchall():
                rating_data = dict(zip(columns, row))
                ratings.append(rating_data)
            
            return ratings
            
    except Exception as e:
        logger.error(f"Ошибка при получении оценок пользователя из базы данных: {e}")
        raise

def load_data_from_csv() -> None:
    """
    Загрузка данных из CSV файлов в базу данных.
    Загружает книги и оценки, если они еще не загружены.
    """
    try:
        import pandas as pd
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже данные в таблице books
            cursor.execute("SELECT COUNT(*) FROM books")
            books_count = cursor.fetchone()[0]
            
            if books_count == 0 and BOOKS_FILE.exists():
                logger.info("Загрузка книг из CSV файла...")
                books_df = pd.read_csv(BOOKS_FILE)
                
                # Подготавливаем данные для вставки
                books_data = []
                for _, row in books_df.iterrows():
                    book_data = {
                        'title_en': row['original_title'],
                        'title_ru': row['title'],  # Используем title как русское название
                        'authors_en': row['authors'],
                        'authors_ru': row['authors'],  # Используем тех же авторов
                        'year': str(row['original_publication_year']),
                        'description': None,  # В CSV нет описаний
                        'genre': None  # В CSV нет жанров
                    }
                    books_data.append(book_data)
                
                # Добавляем книги в базу
                for book_data in books_data:
                    add_book(book_data)
                
                logger.info(f"Загружено {len(books_data)} книг")
            
            # Проверяем, есть ли уже данные в таблице ratings
            cursor.execute("SELECT COUNT(*) FROM ratings")
            ratings_count = cursor.fetchone()[0]
            
            if ratings_count == 0 and RATINGS_FILE.exists():
                logger.info("Загрузка оценок из CSV файла...")
                ratings_df = pd.read_csv(RATINGS_FILE)
                
                # Добавляем оценки в базу
                for _, row in ratings_df.iterrows():
                    try:
                        # Проверяем, что книга существует
                        cursor.execute("SELECT book_id FROM books WHERE book_id = ?", (row['book_id'],))
                        if cursor.fetchone():
                            # Используем user_id из CSV как Telegram user_id
                            # Округляем рейтинг до целого числа от 1 до 5
                            rating = max(1, min(5, round(row['rating'])))
                            add_rating(row['book_id'], row['user_id'], rating)
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении оценки {row['book_id']}: {e}")
                        continue
                
                logger.info(f"Загружено оценок из CSV")
            
            conn.commit()
            
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных из CSV: {e}")
        raise

# Инициализируем базу данных при импорте модуля
init_db()
# Загружаем данные из CSV, если их еще нет
load_data_from_csv() 