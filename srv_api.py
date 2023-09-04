#!/usr/bin/python3

import json
import uuid
from time import time

import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, Session
import jwt


''' =====----- Global variables -----===== '''
# Настройки для SQLAlchemy
DB_PATH = 'sqlite:///sqlite/db.sqlite3'
Base = declarative_base()
ENGINE = sa.create_engine(DB_PATH)
# Время жизни access-token
ACC_TTL = 600.0
# Время жизни refresh-token
REF_TTL = 3600.0
# Ключ для создания JSON Web Token
JWT_KEY = 'secretstring'


''' =====----- Decorators -----===== '''

def auth_decor(fn_to_be_decor):
    ''' Декоратор для функций, которые в именованном аргументе 'req_data'
    получают данные в виде JSON Web Token.
    Распаковывает JWT, проверяет по базе наличие действительного
    access-tokena, по результату передаёт декорируемой функции
    именованный аргумент 'auth_ok' [bool] и полезную нагрузку в
    именованном аргументе 'payload'.
    '''
    def fn_wrapper(**kwargs):
        ok_ = False
        payload_ = dict()
        if 'req_data' in kwargs.keys():
            decoded_jwt_ = jwt.api_jwt.decode_complete(kwargs['req_data'],
                                                       key=JWT_KEY,
                                                       algorithms='HS256')
            token_ = decoded_jwt_['header']['acc_token']
            payload_ = decoded_jwt_['payload']
            try:
                with Session(ENGINE) as s_:
                    user_ = s_.query(User).filter(User.acc_token == token_).first()
                try:
                    if user_.expired > time():
                        # Время действия токена не закончилось
                        ok_ = True
                except:
                    # Токен закончился или его вообще нет
                    ok_ = False
            except:
                # Что-то не так с БД
                ok_ = False
        # Декорируемая функция
        result_ = fn_to_be_decor(auth_ok=ok_, payload=payload_, **kwargs)
        return result_
    return fn_wrapper

''' =====----- API Methods -----===== '''

def login_post(credentials: dict) -> dict:
    ''' Метод для аутентификации на сервере. При логине пользователя
    записывает ему в таблицу "Users" выданные access-token и refresh-token
    и время окончания их действия "acc_expired" и "ref_expired".
    Arguments:
        credentials [dict] -- Словарь/json с ключами "login", "password"
    Returns:
        [dict] -- Словарь/json с ключами "status", "text", "acc_token",
            "acc_expired", "ref_token", "ref_expired"
            или с ключами "status", "text" в случае ошибки
    '''
    output_dict_ = {'status': 'fail',
                    'text': 'Unknown request'
                   }
    try:
        with Session(ENGINE) as s_:
            login_ = credentials['login']
            password_ = credentials['password']
            user_ = s_.query(User).filter(User.login == login_).first()
            if user_:
                if user_.password == password_:
                    acc_token_ = str(uuid.uuid4())
                    ref_token_ = str(uuid.uuid4())
                    # Обновление пользователя в базе
                    user_.acc_token = acc_token_
                    user_.ref_token = ref_token_
                    user_.acc_expired = time() + ACC_TTL
                    user_.ref_expired = time() + REF_TTL
                    s_.add(user_)
                    s_.commit()
                    # Формирование ответа
                    output_dict_['status'] = 'success'
                    output_dict_['text'] = f'User {login_}: logged in'
                    output_dict_['acc_token'] = acc_token_
                    output_dict_['acc_expired'] = user_.acc_expired
                    output_dict_['ref_token'] = ref_token_
                    output_dict_['ref_expired'] = user_.ref_expired
                else:
                    output_dict_['text'] = f'User {login_}: login failed'
            else:
                output_dict_['text'] = f'User {login_}: not exists'
    except Exception as e_:
        print(e_)
    return json.dumps(output_dict_, ensure_ascii=False, indent=2)


#####=====----- THE END -----=====#########################################