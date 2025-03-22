#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Тесты для моделей данных.
"""

import unittest
from src.models.book import Book


class TestBookModel(unittest.TestCase):
    """Тесты для модели Book."""
    
    def test_book_creation(self):
        """Тест создания объекта книги."""
        book = Book(
            title="Тестовая книга",
            author="Тестовый Автор",
            year="2023",
            genre="Тестовый жанр",
            description="Тестовое описание"
        )
        
        self.assertEqual(book.title, "Тестовая книга")
        self.assertEqual(book.author, "Тестовый Автор")
        self.assertEqual(book.year, "2023")
        self.assertEqual(book.genre, "Тестовый жанр")
        self.assertEqual(book.description, "Тестовое описание")
    
    def test_book_to_string(self):
        """Тест преобразования книги в строку."""
        book = Book(
            title="Тестовая книга",
            author="Тестовый Автор",
            year="2023",
            genre="Тестовый жанр",
            description="Тестовое описание"
        )
        
        expected_string = (
            "*Тестовая книга*\n"
            "Автор: Тестовый Автор\n"
            "Год: 2023\n"
            "Жанр: Тестовый жанр\n"
            "Описание: Тестовое описание\n"
        )
        
        self.assertEqual(book.to_string(), expected_string)
    
    def test_book_to_dict(self):
        """Тест преобразования книги в словарь."""
        book = Book(
            title="Тестовая книга",
            author="Тестовый Автор",
            year="2023",
            genre="Тестовый жанр",
            description="Тестовое описание"
        )
        
        expected_dict = {
            "title": "Тестовая книга",
            "author": "Тестовый Автор",
            "year": "2023",
            "genre": "Тестовый жанр",
            "description": "Тестовое описание"
        }
        
        self.assertEqual(book.to_dict(), expected_dict)
    
    def test_book_optional_fields(self):
        """Тест создания книги с опциональными полями."""
        book = Book(
            title="Тестовая книга",
            author="Тестовый Автор"
        )
        
        self.assertEqual(book.title, "Тестовая книга")
        self.assertEqual(book.author, "Тестовый Автор")
        self.assertIsNone(book.year)
        self.assertIsNone(book.genre)
        self.assertIsNone(book.description)


if __name__ == "__main__":
    unittest.main() 