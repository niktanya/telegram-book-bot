# Данные для рекомендательной системы

В этой директории должны находиться файлы с данными для работы рекомендательной системы:

## books.csv
Содержит информацию о книгах:
- `book_id` - уникальный идентификатор книги
- `title` - название книги
- `author` - автор книги
- `year` - год издания
- `genre` - жанр книги
- `description` - краткое описание

Пример структуры:
```
book_id,title,author,year,genre,description
1,"Война и мир","Лев Толстой",1869,"Роман","Эпический роман-эпопея..."
2,"Преступление и наказание","Федор Достоевский",1866,"Роман","Психологический роман..."
```

## book_ratings.csv
Содержит оценки книг пользователями:
- `user_id` - идентификатор пользователя
- `book_id` - идентификатор книги
- `rating` - оценка от 1 до 5

Пример структуры:
```
user_id,book_id,rating
1,1,5
1,2,4
2,1,3
```

## Источники данных
Для наполнения этих файлов можно использовать открытые датасеты, например:
1. [Goodreads Book Reviews](https://sites.google.com/eng.ucsd.edu/ucsdbookgraph/home)
2. [Book-Crossing Dataset](http://www2.informatik.uni-freiburg.de/~cziegler/BX/)
3. [Amazon Book Reviews](https://nijianmo.github.io/amazon/index.html) 