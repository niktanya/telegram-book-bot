import unittest
import json
import asyncio
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from src.services.recommendation import (
    recommend_books,
    recommend_books_collaborative,
    recommend_books_gpt,
    find_closest_book_title
)
from src.services.database import get_all_ratings, get_user_ratings, get_book_by_id

class TestRecommendation(unittest.TestCase):
    def setUp(self):
        """Подготовка к тестам"""
        self.loop = asyncio.get_event_loop()
        
        # Создаем тестовые данные для коллаборативной фильтрации
        self.test_books_df = pd.DataFrame({
            'book_id': [1, 2, 3, 4],
            'title_ru': ['Книга 1', 'Книга 2', 'Книга 3', 'Книга 4'],
            'authors_ru': ['Автор 1', 'Автор 2', 'Автор 3', 'Автор 4'],
            'year': ['2000', '2001', '2002', '2003'],
            'description': ['Описание 1', 'Описание 2', 'Описание 3', 'Описание 4'],
            'genre': ['Жанр 1', 'Жанр 2', 'Жанр 3', 'Жанр 4']
        })
        
        self.test_ratings_df = pd.DataFrame({
            'user_id': [1, 1, 1, 2, 2, 2, 3, 3, 3],
            'book_id': [1, 2, 3, 1, 2, 4, 1, 3, 4],
            'rating': [5, 4, 3, 4, 5, 3, 5, 4, 4]
        })

    def test_recommend_books(self):
        """Тест основной функции рекомендаций"""
        # Мокаем функции базы данных
        with patch('src.services.recommendation.get_all_books', return_value=self.test_books_df), \
             patch('src.services.recommendation.get_all_ratings', return_value=self.test_ratings_df), \
             patch('src.services.recommendation.get_book_by_title', return_value={'book_id': 1}), \
             patch('src.services.recommendation.get_book_by_id', side_effect=lambda x: {
                 'book_id': x,
                 'title_ru': f'Книга {x}',
                 'authors_ru': f'Автор {x}',
                 'year': f'200{x}',
                 'description': f'Описание {x}',
                 'genre': f'Жанр {x}'
             }):
            
            result = self.loop.run_until_complete(
                recommend_books("Книга 1", num_recommendations=3)
            )
            self.assertIsInstance(result, list)
            self.assertLessEqual(len(result), 3)
            
            if result:
                first_book = result[0]
                self.assertIn('title', first_book)
                self.assertIn('authors', first_book)
                self.assertIn('year', first_book)
                self.assertIn('description', first_book)
                self.assertIn('genre', first_book)
                self.assertIn('similarity', first_book)
                self.assertIn('book_id', first_book)

    def test_recommend_books_collaborative(self):
        """Тест коллаборативной фильтрации"""
        # Мокаем функции базы данных
        with patch('src.services.recommendation.get_all_books', return_value=self.test_books_df), \
             patch('src.services.recommendation.get_all_ratings', return_value=self.test_ratings_df), \
             patch('src.services.recommendation.get_book_by_title', return_value={'book_id': 1}), \
             patch('src.services.recommendation.get_book_by_id', side_effect=lambda x: {
                 'book_id': x,
                 'title_ru': f'Книга {x}',
                 'authors_ru': f'Автор {x}',
                 'year': f'200{x}',
                 'description': f'Описание {x}',
                 'genre': f'Жанр {x}'
             }):
            
            result = self.loop.run_until_complete(
                recommend_books_collaborative("Книга 1", num_recommendations=3)
            )
            self.assertIsInstance(result, list)
            self.assertLessEqual(len(result), 3)
            
            if result:
                first_book = result[0]
                self.assertIn('title', first_book)
                self.assertIn('authors', first_book)
                self.assertIn('year', first_book)
                self.assertIn('description', first_book)
                self.assertIn('genre', first_book)
                self.assertIn('similarity', first_book)
                self.assertIn('book_id', first_book)
                # Проверяем, что схожесть - это число с плавающей точкой
                self.assertIsInstance(first_book['similarity'], float)
                # Проверяем, что схожесть в допустимом диапазоне
                self.assertGreaterEqual(first_book['similarity'], 0)
                self.assertLessEqual(first_book['similarity'], 1)

    def test_recommend_books_gpt(self):
        """Тест рекомендаций через GPT"""
        # Мокаем GPT
        with patch('src.services.recommendation.client.chat.completions.create') as mock_gpt:
            mock_gpt.return_value.choices = [
                MagicMock(message=MagicMock(content=json.dumps({
                    "original_book": {"title": "Тестовая книга", "authors": "Тестовый автор"},
                    "recommendations": [{
                        "title": "GPT книга",
                        "authors": "GPT автор",
                        "year": "2023",
                        "description": "Тестовое описание",
                        "genre": "Тестовый жанр",
                        "similarity": "Похожа по жанру и стилю"
                    }]
                })))
            ]
            
            result = self.loop.run_until_complete(
                recommend_books_gpt("Тестовая книга", 3)
            )
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            self.assertIn('title', result[0])
            self.assertIn('similarity', result[0])
            # В GPT-рекомендациях similarity может быть строкой
            self.assertIsInstance(result[0]['similarity'], str)

    def test_recommendations_format(self):
        """Тест формата рекомендаций"""
        # Мокаем функции базы данных
        with patch('src.services.recommendation.get_all_books', return_value=self.test_books_df), \
             patch('src.services.recommendation.get_all_ratings', return_value=self.test_ratings_df), \
             patch('src.services.recommendation.get_book_by_title', return_value={'book_id': 1}), \
             patch('src.services.recommendation.get_book_by_id', side_effect=lambda x: {
                 'book_id': x,
                 'title_ru': f'Книга {x}',
                 'authors_ru': f'Автор {x}',
                 'year': f'200{x}',
                 'description': f'Описание {x}',
                 'genre': f'Жанр {x}'
             }):
            
            result = self.loop.run_until_complete(
                recommend_books("Книга 1", num_recommendations=3)
            )
            
            for book in result:
                # Проверяем наличие всех необходимых полей
                self.assertIn('title', book)
                self.assertIn('authors', book)
                self.assertIn('year', book)
                self.assertIn('description', book)
                self.assertIn('genre', book)
                self.assertIn('similarity', book)
                self.assertIn('book_id', book)
                
                # Проверяем типы данных
                self.assertIsInstance(book['title'], str)
                self.assertIsInstance(book['authors'], str)
                self.assertIsInstance(book['year'], str)
                self.assertIsInstance(book['description'], str)
                self.assertIsInstance(book['genre'], str)
                self.assertIsInstance(book['similarity'], (float, str))  # Может быть float для коллаб. фильтрации или str для GPT
                self.assertIsInstance(book['book_id'], int)
                
                # Проверяем, что значения не пустые
                self.assertTrue(book['title'])
                self.assertTrue(book['authors'])
                self.assertTrue(book['year'])
                self.assertTrue(book['description'])
                self.assertTrue(book['genre'])
                self.assertTrue(book['book_id'])
                
                # Проверяем схожесть в зависимости от типа
                if isinstance(book['similarity'], float):
                    self.assertGreaterEqual(book['similarity'], 0)
                    self.assertLessEqual(book['similarity'], 1)
                else:
                    self.assertIsInstance(book['similarity'], str)
                    self.assertTrue(book['similarity'])

    def test_get_user_ratings(self):
        """Тест получения оценок пользователя"""
        # Получаем все оценки
        ratings_df = get_all_ratings()
        if ratings_df.empty:
            self.skipTest("В базе данных нет оценок")
        
        # Берем ID первого пользователя с оценками
        first_user_id = int(ratings_df.iloc[0]['user_id'])
        
        # Тестируем получение оценок существующего пользователя
        ratings = get_user_ratings(first_user_id)
        self.assertIsInstance(ratings, list)
        self.assertTrue(len(ratings) > 0)
        self.assertIn('rating', ratings[0])
        self.assertIn('title_ru', ratings[0])
        
        # Тестируем получение оценок несуществующего пользователя
        ratings = get_user_ratings(999999)
        self.assertIsInstance(ratings, list)
        self.assertEqual(len(ratings), 0)

if __name__ == '__main__':
    unittest.main() 