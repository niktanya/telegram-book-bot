# Данные для рекомендательной системы

В этой директории должны находиться файлы с данными для работы рекомендательной системы:

## books.csv
Содержит информацию о книгах:
- `book_id` - уникальный идентификатор книги
- `isbn` - международный стандартный книжный номер
- `isbn13` - международный стандартный книжный номер (13-значный новый стандарт с 2007 года)
- `authors` - авторы книги
- `original_publication_year` - год издания
- `original_title` - название книги
- `title` - более детальное название книги (с указанием названия основной серии книг и номера части)
- `average_rating` - средний рейтинг книги

Пример структуры:
```
book_id,isbn,isbn13,authors,original_publication_year,original_title,title,average_rating
1,439023483,9780439023480,Suzanne Collins,2008,The Hunger Games,"The Hunger Games (The Hunger Games, #1)",4.34
2,439554934,9780439554930,"J.K. Rowling, Mary GrandPré",1997,Harry Potter and the Philosopher's Stone,"Harry Potter and the Sorcerer's Stone (Harry Potter, #1)",4.44
3,316015849,9780316015840,Stephenie Meyer,2005,Twilight,"Twilight (Twilight, #1)",3.57
```

## book_ratings.csv
Содержит оценки книг пользователями:
- `user_id` - идентификатор пользователя
- `book_id` - идентификатор книги
- `rating` - оценка от 1 до 5

Пример структуры:
```
user_id,book_id,rating
1,258,5
2,4081,4
2,260,5
```

# Источники данных

В данном проекте используется датасет [Goodreads-10K](https://www.kaggle.com/datasets/sahilkirpekar/goodreads10k-dataset-cleaned)

Примеры других открытых датасетов:
1. [Goodreads Book Reviews](https://sites.google.com/eng.ucsd.edu/ucsdbookgraph/home)
2. [Book-Crossing Dataset](http://www2.informatik.uni-freiburg.de/~cziegler/BX/)
3. [Amazon Book Reviews](https://nijianmo.github.io/amazon/index.html) 