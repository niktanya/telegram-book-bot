import unittest
from services.database import (
    get_all_books,
    get_all_ratings,
    get_book_by_title,
    get_book_by_id,
    get_user_ratings,
    add_book,
    add_rating
)
import sqlite3
from services.database import DB_FILE

class TestDatabase(unittest.TestCase):
    def test_get_all_books(self):
        """Тест получения всех книг"""
        books_df = get_all_books()
        self.assertFalse(books_df.empty)
        self.assertIn('book_id', books_df.columns)
        self.assertIn('title_ru', books_df.columns)

    def test_get_all_ratings(self):
        """Тест получения всех оценок"""
        ratings_df = get_all_ratings()
        self.assertFalse(ratings_df.empty)
        self.assertIn('user_id', ratings_df.columns)
        self.assertIn('book_id', ratings_df.columns)
        self.assertIn('rating', ratings_df.columns)

    def test_get_book_by_title(self):
        """Тест поиска книги по названию"""
        # Тестируем поиск существующей книги
        book = get_book_by_title("Гарри Поттер")
        self.assertIsNotNone(book)
        self.assertIn('title_ru', book)
        
        # Тестируем поиск несуществующей книги
        book = get_book_by_title("НесуществующаяКнига123456")
        self.assertIsNone(book)

    def test_get_book_by_id(self):
        """Тест получения книги по ID"""
        # Получаем все книги
        books_df = get_all_books()
        if books_df.empty:
            self.skipTest("В базе данных нет книг")
            
        # Берем ID первой книги, которая точно есть в базе
        first_book_id = int(books_df.iloc[0]['book_id'])
        
        # Тестируем получение существующей книги
        book = get_book_by_id(first_book_id)
        self.assertIsNotNone(book)
        self.assertEqual(book['book_id'], first_book_id)
        
        # Тестируем получение несуществующей книги
        book = get_book_by_id(999999)
        self.assertIsNone(book)

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
        ratings = get_user_ratings(999998)  # гарантированно несуществующий user_id
        self.assertIsInstance(ratings, list)
        self.assertEqual(len(ratings), 0)

    def test_add_and_get_rating(self):
        """Тест добавления и получения оценки"""
        # Добавляем тестовую книгу
        test_book = {
            'title_en': 'Test Book',
            'title_ru': 'Тестовая Книга',
            'authors_en': 'Test Author',
            'authors_ru': 'Тестовый Автор',
            'year': '2024',
            'description': 'Test description',
            'genre': 'Test'
        }
        book_id = add_book(test_book)
        
        # Добавляем оценку
        test_user_id = 999999
        test_rating = 5
        add_rating(book_id, test_user_id, test_rating)
        
        # Проверяем, что оценка добавилась
        ratings = get_user_ratings(test_user_id)
        self.assertTrue(len(ratings) > 0)
        self.assertTrue(any(
            (r['book_id'] == book_id and r['rating'] == test_rating) for r in ratings
        ))
        # Удаляем тестовую оценку и книгу
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ratings WHERE user_id = ? AND book_id = ?", (test_user_id, book_id))
            cursor.execute("DELETE FROM books WHERE book_id = ?", (book_id,))
            conn.commit()

if __name__ == '__main__':
    unittest.main() 