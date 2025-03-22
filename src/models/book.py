#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модель для представления книги.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Book:
    """
    Класс для представления книги.
    """
    title: str
    author: str
    year: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    
    def to_string(self) -> str:
        """
        Преобразует информацию о книге в строку для вывода пользователю.
        
        Returns:
            Строка с информацией о книге
        """
        result = f"*{self.title}*\n"
        result += f"Автор: {self.author}\n"
        
        if self.year:
            result += f"Год: {self.year}\n"
        
        if self.genre:
            result += f"Жанр: {self.genre}\n"
        
        if self.description:
            result += f"Описание: {self.description}\n"
        
        return result
    
    def to_dict(self) -> dict:
        """
        Преобразует объект книги в словарь.
        
        Returns:
            Словарь с данными книги
        """
        return {
            "title": self.title,
            "author": self.author,
            "year": self.year,
            "description": self.description,
            "genre": self.genre
        } 