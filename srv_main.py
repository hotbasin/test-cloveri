#!/usr/bin/python3

from bottle import HTTPError, get, post, request, run

import srv_api as api_


''' =====----- Server resources -----===== '''

@post('/auth/login')
def login_post() -> dict:
    ''' Ресурс аутентификации на сервере через метод POST
    '''
    return api_.login_post(request.json)


@get('/users/all')
def all_users_get() -> dict:
    ''' Ресурс выдачи всей базы врачей и клиентов
    '''
    return api_.all_users_get(req_data=request.query.req_data)


@post('/coords/update')
def coords_update_post() -> dict:
    ''' Ресурс для добавления в базу новых координат врача
    '''
    return api_.coords_update_post(request.json)


''' =====----- MAIN -----===== '''

if __name__ == '__main__':
    run(host='0.0.0.0', port=8080, debug=True)

#####=====----- THE END -----=====#########################################