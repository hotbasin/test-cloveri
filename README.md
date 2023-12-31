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

В самом начале разработки не забыть организовать аутентификацию OAuth2.
Например, не обязательно с авторизацией через API Google или неких соцсетей, а,
допустим с помощью JSON Web Token (JWT).

Например, клиентское приложение (далее&nbsp;&mdash; клиент) посылает на ресурс
`/auth/login` API сервера (далее&nbsp;&mdash; сервер) HTTP-методом `POST`
словарь/json с ключами `login` и `password`. В ответ получает словарь/json с
результатом. В случае успешной аутентификации добавляет в ответ Access-token
(с коротким time-to-live (TTL), например 10&nbsp;минут) и Refresh-token (с более
длинным TTL, сравнимым с рабочим днём врача, например 10&nbsp;часов).

При дальнейших запросах на сервер клиент пакует сам запрос в payload-часть JSON
Web Token (JWT) и Access-token в header-часть JWT для авторизации запроса. По
окончании TTL Access-токена клиент в фоновом режиме запрашивает у сервера с
помощью Refresh-токена новый Access-токен. При истечении TTL Refresh-токена
клиенту надо заново вводить логин/пароль для аутентификации.

За раскодировку JWT, проверку Access-токена и передачу payload-части методам API
сервера отвечает отдельный универсальный декоратор.

Примерная реализация (Сервер `Bottle`, база `SQLite`) приведена в следующих
файлах:

[**`srv_main.py`**](srv_main.py)&nbsp;&mdash; содержит определения требуемых
ресурсов.

[**`srv_api.py`**](srv_api.py)&nbsp;&mdash; для примера собраны некоторые методы
API, импортируемые в [`srv_main.py`](srv_main.py).

----

Если предположить использование СУБД PostgreSQL, то для упрощения чистых
SQL-запросов, применяя `Pandas` и `Psycopg2` можно определить функцию
`make_request()`, которая далее используется в примерах:

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
    ''' Принимает SQL-запрос в виде строки или многострочника.
        Возвращает Pandas-dataframe.
    '''
    with pc.connect(**CONN_ATTRIBS) as conn:
        return pd.read_sql_query(query, conn)
```

## Ответ на вопрос 1 и 2 ##

*(Предложить описание используемых таблиц в базе данных, включая информацию о
названиях и формате полей.)*

*(Предложить индексы для каждой из таблиц, которые помогут быстрее выдавать
информацию по идентификатору врача.)*

В базе данных 6 таблиц. Конечно, каждую из них можно дополнить новыми колонками.

### Users ###

Таблица с данными для авторизации/аутентификации, где доктора и пациенты вместе.

    user_id     UUID    Уникальный идентификатор пользователя системы (Primary key)
    is_doc      BOOL    Доктор (True) или пациент (False)
    name        TEXT    ФИО пользователя
    login       TEXT    Имя пользователя в системе
    password    TEXT    Пароль пользователя в системе
    acc_token   UUID    Access-token (аутентификация OAuth2)
    acc_expire  FLOAT   Время окончания действия Access-token (unix-time, seconds)
    ref_token   UUID    Refresh-token (аутентификация OAuth2)
    ref_expire  FLOAT   Время окончания действия Refresh-token (unix-time, seconds)

### Doctors ###

Таблица для участковых врачей

    user_id     UUID    Уникальный идентификатор доктора (Primary key)
                        (идентичен users.user_id)
    city_id     UUID    Уникальный идентификатор города
                        (идентичен cities.city_id)
    dist_id     UUID    Уникальный идентификатор участка
                        (идентичен districts.dist_id)
    day_route   TEXT    Текущий дневной маршрут доктора (список пациентов)

### Clients ###

Таблица для пациентов

    user_id     UUID    Уникальный идентификатор пациента (Primary key)
                        (идентичен users.user_id)
    address     TEXT    Адрес пациента
    city_id     UUID    Уникальный идентификатор города
                        (идентичен cities.city_id)
    dist_id     UUID    Уникальный идентификатор участка
                        (идентичен districts.dist_id)
    doc_id      UUID    Уникальный идентификатор лечащего врача
    lat         FLOAT   Широта
    lng         FLOAT   Долгота

### Cities ###

Дополнительная таблица городов, где работают участковые врачи и живут пациенты,
которая может пригодиться в будущем.

    city_id     UUID    Уникальный идентификатор города (Primary key)
    name        TEXT    Название города

### Districts ###

Дополнительная таблица участков, которая может пригодиться в будущем.

    dist_id     UUID    Уникальный идентификатор участка (Primary key)
    name        TEXT    Название (номер) участка
    city_id     UUID    Уникальный идентификатор города
                        (идентичен cities.city_id)

### Positions ###

Таблица, в которую постоянно заносятся координаты врачей.

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
    "user_id": "10abcd01-ef11-1ff1-11ed-10accb000001",
    "upd_time": 1693742003.8034012,
    "lat": 55.755833,
    "lng": 37.617778
}
```

Этот словарь/json упаковывается на клиентском приложении врача в JWT (в
payload-часть) и передаётся на сервер.

[:arrow_up: Содержание](#содержание)

----

## Ответ на вопрос 4 ##

*(Написать SQL-запрос, который выведет информацию о врачах, которые в последние
10 минут переместились более чем на 1 км.)*

Чтобы не загружать БД лишними вычислениями при SQL-запросе, просто запрашиваем
врачей, у которых за последние 10 минут есть записи в таблице `Positions`.

```python
from time import time

check_interval = 600
check_time = str(time() - check_interval)

query_str = f'''
SELECT
    p.user_id AS uid,
    u.name AS name,
    p.upd_time AS upd_time,
    p.lat AS lat,
    p.lng AS lng
FROM db_name.Positions AS p
JOIN db_name.users AS u ON p.user_id = u.user_id
WHERE
    upd_time > {check_time}
ORDER BY user_id, upd_time
'''

query_df = make_request(query_str)
```

Далее работаем с датафреймом `query_df`. Выбираем тех врачей в список
`ini_doc_list``, у которых не меньше двух записей координат. У кого больше двух
точек&nbsp;&mdash; последовательно вычисляем расстояние между точками и
суммируем пройденный путь (конечно же, вычисляем расстояние по прямой, будто он
летит на вертолёте, а не идёт по улицам :wink:). Это можно сделать, сначала в
цикле формируя для каждого врача список кортежей с координатами точек:

```python
doc_coords = [(lat1, lng1), (lat2, lng2),...]
```

И далее для вычисления расстояний по геокоординатам использовать `geopy`.

```bash
pip install geopy
```

Там достаточно передать ему два кортежа с геокоординатами широты и долготы двух
точек. В функции API будет примерно такие строки:


```python
from geopy.distance import geodesic as gd

output_doc_list = []
for n in range(len(doc_coords) - 1):
    path_length = 0
    coords0 = doc_coords[n]
    coords1 = doc_coords[n+1]
    path_length += gd(coords0, coords1).km
if path_length > 1.0:
    # Этот врач прошёл более 1км. Добавляем его в список output_doc_list,
    # который будет использоваться на выдаче.
    output_doc_list.append(doc_uuid)
```

[:arrow_up: Содержание](#содержание)

----

## Ответ на вопрос 5 ##

*(Написать SQL-запрос, который выведет всех врачей, для которых нет информации
об их перемещениях за последний час.)*

```python
from time import time

check_interval = 3600
check_time = str(time() - check_interval)

query_str = f'''
SELECT
    p.user_id AS uid,
    u.name AS name,
    MAX(p.upd_time) AS upd_time,
FROM db_name.Positions AS p
JOIN db_name.Users AS u ON p.user_id = u.user_id
GROUP BY p.user_id
HAVING MAX(p.upd_time) < {check_time}
ORDER BY u.name
'''

query_df = make_request(query_str)
```

И теперь из полученного датафрейма `query_df` мы можем выдать клиентскому
приложению соответствующий словарь/json:

```python
import json

json_dict = json.loads(query_df.to_json())
json.dumps(json_dict, ensure_ascii=False, indent=2)
```

[:arrow_up: Содержание](#содержание)

----
