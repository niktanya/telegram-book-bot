import unittest
import json
import asyncio
from services.recommendation import (
    recommend_books,
    recommend_books_collaborative,
    recommend_books_gpt
)
from services.database import get_all_ratings, get_user_ratings

class TestRecommendation(unittest.TestCase):
    def setUp(self):
        """Подготовка к тестам"""
        self.loop = asyncio.get_event_loop()

    def test_recommend_books(self):
        """Тест основной функции рекомендаций"""
        # Тестируем рекомендации для существующей книги
        result = self.loop.run_until_complete(
            recommend_books("Гарри Поттер", 3)
        )
        recommendations = json.loads(result)
        self.assertIsInstance(recommendations, list)
        self.assertLessEqual(len(recommendations), 3)
        
        if recommendations:
            first_book = recommendations[0]
            self.assertIn('title', first_book)
            self.assertIn('authors', first_book)
            self.assertIn('year', first_book)
            self.assertIn('description', first_book)
            self.assertIn('genre', first_book)
            self.assertIn('similarity', first_book)

    def test_recommend_books_collaborative(self):
        """Тест коллаборативной фильтрации"""
        # Тестируем рекомендации для существующей книги
        result = self.loop.run_until_complete(
            recommend_books_collaborative("Гарри Поттер", 3)
        )
        recommendations = json.loads(result)
        self.assertIsInstance(recommendations, list)
        self.assertLessEqual(len(recommendations), 3)
        
        if recommendations:
            first_book = recommendations[0]
            self.assertIn('title', first_book)
            self.assertIn('authors', first_book)
            self.assertIn('year', first_book)
            self.assertIn('description', first_book)
            self.assertIn('genre', first_book)
            self.assertIn('similarity', first_book)
            self.assertIsInstance(first_book['similarity'], float)

    def test_recommend_books_gpt(self):
        """Тест рекомендаций через GPT"""
        # Тестируем рекомендации для несуществующей книги
        result = self.loop.run_until_complete(
            recommend_books_gpt("НесуществующаяКнига123456", 3)
        )
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_recommendations_format(self):
        """Тест формата рекомендаций"""
        result = self.loop.run_until_complete(
            recommend_books("Гарри Поттер", 3)
        )
        recommendations = json.loads(result)
        
        for book in recommendations:
            # Проверяем наличие всех необходимых полей
            self.assertIn('title', book)
            self.assertIn('authors', book)
            self.assertIn('year', book)
            self.assertIn('description', book)
            self.assertIn('genre', book)
            self.assertIn('similarity', book)
            
            # Проверяем типы данных
            self.assertIsInstance(book['title'], str)
            self.assertIsInstance(book['authors'], str)
            self.assertIsInstance(book['year'], str)
            self.assertIsInstance(book['description'], str)
            self.assertIsInstance(book['genre'], str)
            self.assertIsInstance(book['similarity'], float)
            
            # Проверяем, что значения не пустые
            self.assertTrue(book['title'])
            self.assertTrue(book['authors'])
            self.assertTrue(book['year'])
            self.assertTrue(book['description'])
            self.assertTrue(book['genre'])
            self.assertGreaterEqual(book['similarity'], 0)
            self.assertLessEqual(book['similarity'], 1)

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