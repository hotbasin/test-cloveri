# Тестовое задание по Backend-разработке приложения для участковых врачей #

## Содержание ##

[Условия задания](#условия-задания)    
[Общее описание решения](#общее-описание-решения)    
[Ответ на вопрос 1 и 2](#ответ-на-вопрос-1-и-2)    
[Ответ на вопрос 3](#ответ-на-вопрос-3)    
[Ответ на вопрос 4](#ответ-на-вопрос-4)    
[Ответ на вопрос 5](#ответ-на-вопрос-5)    

## Условия задания ##

Вы участвуете в разработке мобильного приложения для участковых врачей.

Ваш менеджер говорит, что новую фичу приложения будут использовать врачи при
посещении больных. Приложение должно отправлять на сервера проекта информацию о
геопозиции врача. А пациенты будут отслеживать местоположение своего участкового
врача в своем приложении.

Ваша задача&nbsp;&mdash; спроектировать хранилище такой информации и API для
записи в него.

Основная цель новой фичи&nbsp;&mdash; запоминать местонахождение каждого врача и
выводить информацию о враче (имя, последние координаты, маршрут).

1. Предложить описание используемых таблиц в базе данных, включая информацию о
названиях и формате полей. [Ответ на вопрос 1](#ответ-на-вопрос-1-и-2)
2. Предложить индексы для каждой из таблиц, которые помогут быстрее выдавать
информацию по идентификатору врача. [Ответ на вопрос 2](#ответ-на-вопрос-1-и-2)
3. Какие параметры должно принимать API на серверах проекта, чтобы можно было
сохранять местонахождение того или иного врача? [Ответ на вопрос 3](#ответ-на-вопрос-3)
4. Написать SQL-запрос, который выведет информацию о врачах, которые в последние
10 минут переместились более чем на 1 км. [Ответ на вопрос 4](#ответ-на-вопрос-4)
5. Написать SQL-запрос, который выведет всех врачей, для которых нет информации
об их перемещениях за последний час. [Ответ на вопрос 5](#ответ-на-вопрос-5)

[:arrow_up: Содержание](#содержание)

----

## Общее описание решения ##

- В самом начале разработки не забыть аутентификацию OAuth2.

- Для упрощения чистых SQL-запросов можно задать функцию `make_request()`:

```python
import pandas as pd
import psycopg2 as pc

CONN_ATTRIBS = {
    'user': 'Login_Name',
    'password': 'qwerty123',
    'host': '127.0.0.4',
    'port': 5432,
    'dbname': 'db_name'
}

def make_request(query: str) -> object:
    with pc.connect(**CONN_ATTRIBS) as conn:
        return pd.read_sql_query(query, conn)
```

## Ответ на вопрос 1 и 2 ##

*(Предложить описание используемых таблиц в базе данных, включая информацию о
названиях и формате полей.)*

*(Предложить индексы для каждой из таблиц, которые помогут быстрее выдавать
информацию по идентификатору врача.)*

В базе данных 6 таблиц:

### users ###

    user_id     UUID    Уникальный идентификатор пользователя системы (Primary key)
    is_doc      BOOL    Доктор (True) или пациент (False)
    name        TEXT    ФИО пользователя
    login       TEXT    Имя пользователя в системе
    password    TEXT    Пароль пользователя в системе
    acc_token   UUID    Access-token (аутентификация OAuth2)
    acc_expire  FLOAT   Время окончания действия Access-token (unix-time, seconds)
    ref_token   UUID    Refresh-token (аутентификация OAuth2)
    ref_expire  FLOAT   Время окончания действия Refresh-token (unix-time, seconds)

### doctors ###

    user_id     UUID    Уникальный идентификатор доктора (Primary key)
    city_id     UUID    Уникальный идентификатор города
    distr_id    UUID    Уникальный идентификатор участка
    day_route   TEXT    Текущий дневной маршрут доктора (список пациентов)

### clients ###

    user_id     UUID    Уникальный идентификатор пациента (Primary key)
    address     TEXT    Адрес пациента
    city_id     UUID    Уникальный идентификатор города
    distr_id    UUID    Уникальный идентификатор участка
    doc_id      UUID    Уникальный идентификатор лечащего врача
    lat         FLOAT   Широта
    lng         FLOAT   Долгота

### cities ###

    city_id     UUID    Уникальный идентификатор города (Primary key)
    name        TEXT    Название города

### districts ###

    dist_id     UUID    Уникальный идентификатор участка (Primary key)
    name        TEXT    Название (номер) участка
    city_id     UUID    Уникальный идентификатор города

### positions ###

    user_id     UUID    Уникальный идентификатор доктора
    upd_time    FLOAT   Время записи (unix-time, seconds)
    lat         FLOAT   Широта
    lng         FLOAT   Долгота

----

[:arrow_up: Содержание](#содержание)

----

## Ответ на вопрос 3 ##

*(Какие параметры должно принимать API на серверах проекта, чтобы можно было
сохранять местонахождение того или иного врача?)*

Можно принимать в формате словаря/json. Например:

```json
{
    "user_id": "10000001-1111-1111-1111-100000000001",
    "upd_time": 1693742003.8034012,
    "lat": 55.755833,
    "lng": 37.617778
}
```

Этот словарь/json упаковывается в JWT (раздел payload).

[:arrow_up: Содержание](#содержание)

----

## Ответ на вопрос 4 ##

*(Написать SQL-запрос, который выведет информацию о врачах, которые в последние
10 минут переместились более чем на 1 км.)*

Чтобы не загружать БД лишними вычислениями при SQL-запросе, просто запрашиваем
врачей, у которых за последние 10 минут есть записи в таблице `positions`.

```python
from time import time

check_interval = 600
check_time = str(time() - check_interval)

query_str = f'''
SELECT
    user_id,
    upd_time,
    lat,
    lng
FROM db_name.positions
WHERE
    upd_time > {check_time}
ORDER BY user_id, upd_time
'''

query_df = make_request(query_str)
```

И далее для вычисления расстояний по геокоординатам использовать `geopy`.

```bash
pip install geopy
```

```python
from geopy.distance import geodesic as g_

point1 = (40.7128, 74.0060)
point2 = (31.9686, 99.9018)
print('The distance is:', g_(point1, point2).km)
```

[:arrow_up: Содержание](#содержание)

----

## Ответ на вопрос 5 ##

*(Написать SQL-запрос, который выведет всех врачей, для которых нет информации
об их перемещениях за последний час.)*

[:arrow_up: Содержание](#содержание)

----
