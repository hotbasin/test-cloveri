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
REF_TTL = 36000.0
# Ключ для создания JSON Web Token
JWT_KEY = 'secretstring'


''' =====----- Classes -----===== '''

class User(Base):
    __tablename__ = 'Users'
    user_id = sa.Column(sa.String(36), primary_key=True)
    is_doc = sa.Column(sa.Boolean)
    name = sa.Column(sa.String(1024))
    login = sa.Column(sa.String(1024))
    password = sa.Column(sa.String(1024))
    acc_token = sa.Column(sa.String(36))
    acc_expire = sa.Column(sa.Float)
    ref_token = sa.Column(sa.String(36))
    ref_expire = sa.Column(sa.Float)

class Positions(Base):
    __tablename__ = 'Positions'
    user_id = sa.Column(sa.String(36), primary_key=True)
    upd_time = sa.Column(sa.Float)
    lat = sa.Column(sa.Float)
    lng = sa.Column(sa.Float)


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
                    if user_.expire > time():
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
                    user_.acc_expire = time() + ACC_TTL
                    user_.ref_expire = time() + REF_TTL
                    s_.add(user_)
                    s_.commit()
                    # Формирование ответа
                    output_dict_['status'] = 'success'
                    output_dict_['text'] = f'User {login_}: logged in'
                    output_dict_['acc_token'] = acc_token_
                    output_dict_['acc_expire'] = user_.acc_expired
                    output_dict_['ref_token'] = ref_token_
                    output_dict_['ref_expire'] = user_.ref_expired
                else:
                    output_dict_['text'] = f'User {login_}: login failed'
            else:
                output_dict_['text'] = f'User {login_}: not exists'
    except Exception as e_:
        print(e_)
    return json.dumps(output_dict_, ensure_ascii=False, indent=2)


@auth_decor
def all_users_get(auth_ok=False, payload=None, **kwargs):
    ''' Метод для выдачи всей базы врачей и клиентов
    Keyword Arguments:
        auth_ok [bool] -- Запрос аутентифицирован
        payload [dict] -- Распакованная из JWT полезная нагрузка
            (словарь/json)
    Returns:
        [dict] -- Словарь/json с ключами status/text/all_abon
            или с ключами status/text в случае ошибки
    '''
    output_dict_ = {'status': 'fail',
                    'text': 'Unknown request'
                   }
    if auth_ok:
        try:
            with Session(ENGINE) as s_:
                users_ = s_.query(Users).all()
            n_ = 0
            user_dict_ = {}
            for user_ in users_:
                n_ += 1
                user_dict_[n_] = dict(name=abon_.name,
                                      login=abon_.login,
                                      is_doc=str(abon_.is_doc)
                                     )
            output_dict_['status'] = 'success'
            output_dict_['text'] = 'Authorized request'
            output_dict_['all_abon'] = abon_dict_
        except:
            # Ошибки работы с БД
            output_dict_['text'] = 'DS access error'
    else:
        # Токен закончился, надо обновить (снова залогиниться)
        output_dict_['text'] = 'Login required'
    return json.dumps(output_dict_, ensure_ascii=False, indent=2)


@auth_decor
def coords_update_post(auth_ok=False, payload=None, **kwargs) -> dict:
    ''' Метод для добавления текущих координат врача в базу
    Arguments:
        auth_ok [bool] -- Запрос аутентифицирован
        payload [dict] -- Распакованная из JWT полезная нагрузка
            (словарь/json)
    Returns:
        [dict] -- Словарь/json с ключами status/text
    '''
    output_dict_ = {'status': 'fail',
                    'text': 'Unknown request'
                   }
    if auth_ok:
        new_coords = Positions(user_id=payload['user_id'],
                               upd_time=payload['upd_time'],
                               lat=payload['lat'],
                               lng=payload['lng']
                              )
        try:
            with Session(ENGINE) as s_:
                s_.add(new_coords)
                s_.commit()
                output_dict_['status'] = 'success'
                output_dict_['text'] = 'New coordinates recorded'
        except:
            # Ошибки работы с БД
            output_dict_['text'] = 'DB access error'
    else:
        # Токен закончился, надо обновить
        output_dict_['text'] = 'Needs refresh token'
    return json.dumps(output_dict_, ensure_ascii=False, indent=2)

#####=====----- THE END -----=====#########################################