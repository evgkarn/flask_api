# -*- coding: utf-8 -*-
from numpy import unicode
from app import app, models, db
from flask import jsonify, abort, request, make_response, url_for
from flask_httpauth import HTTPBasicAuth

auth = HTTPBasicAuth()
app.config['JSON_AS_ASCII'] = False


@auth.get_password
def get_password(username):
    if username == 'miguel':
        return 'python'
    return None


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 403)


ads = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol',
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web',
        'done': False
    }
]


def make_public_task(task):
    new_task = {}
    for field in task:
        if field == 'id':
            new_task['uri'] = url_for('get_task', task_id=task['id'], _external=True)
        else:
            new_task[field] = task[field]
    return new_task


@app.route('/todo/api/v1.0/ads', methods=['GET'])
def get_ads():
    return jsonify({'ads': list(map(make_public_task, ads))})


@app.route('/todo/api/v1.0/ads/<int:task_id>', methods=['GET'])
@auth.login_required
def get_task(task_id):
    task = list(filter(lambda t: t['id'] == task_id, ads))
    if len(task) == 0:
        abort(404)
    return jsonify({'task': task[0]})


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


# Формирования словаря полей пользователя для json ответа
def ad_by_id(id_elem):
    ad = models.Post.query.get(id_elem)
    new_ad_json = {
        'id': ad.id,
        'name': ad.name_ads,
        'text': ad.body,
        'mark_auto': ad.mark_auto,
        'model_auto': ad.model_auto,
        'year_auto': ad.year_auto,
        'vin_auto': ad.vin_auto,
        'price': ad.price,
        'url': url_for('get_ad', user_id=ad.id, _external=True)
    }
    return new_ad_json


@app.route('/todo/api/v1.0/ads', methods=['POST'])
# @auth.login_required
def create_ads():
    if not request.json or not 'text' in request.json:
        abort(400)
    ads = models.Post.query.all()
    if ads:
        id_ad = ads[-1].id + 1
    else:
        id_ad = 1
    new_ad = models.Post(
        id=id_ad,
        name_ads=request.json.get('name', ""),
        body=request.json.get('text', ""),
        mark_auto=request.json['mark_auto'],
        model_auto=request.json['model_auto'],
        year_auto=request.json['year_auto'],
        vin_auto=request.json['vin_auto'],
        price=request.json['price'],
        user_id=request.json['user_id']
    )
    db.session.add(new_ad)
    db.session.commit()
    return jsonify(ad_by_id(id_ad))


@app.route('/todo/api/v1.0/ads/<int:task_id>', methods=['PUT'])
@auth.login_required
def update_task(task_id):
    task = list(filter(lambda t: t['id'] == task_id, ads))
    if len(task) == 0:
        abort(404)
    if not request.json:
        abort(400)
    if 'title' in request.json and type(request.json['title']) != unicode:
        abort(400)
    if 'description' in request.json and type(request.json['description']) is not unicode:
        abort(400)
    if 'done' in request.json and type(request.json['done']) is not bool:
        abort(400)
    task[0]['title'] = request.json.get('title', task[0]['title'])
    task[0]['description'] = request.json.get('description', task[0]['description'])
    task[0]['done'] = request.json.get('done', task[0]['done'])
    return jsonify({'task': task[0]})


@app.route('/todo/api/v1.0/ads/<int:task_id>', methods=['DELETE'])
@auth.login_required
def delete_task(task_id):
    task = list(filter(lambda t: t['id'] == task_id, ads))
    print(task)
    if len(task) == 0:
        abort(404)
    ads.remove(task[0])
    return jsonify({'result': True})


# Формирования словаря полей пользователя для json ответа
def user_by_id(id_elem):
    user = models.User.query.get(id_elem)
    new_user_json = {
        'id': user.id,
        'nickname': user.nickname,
        'password': user.password,
        'email': user.email,
        'role': user.role,
        'url': url_for('get_user', user_id=user.id, _external=True)
    }
    return new_user_json


# Получить всех пользователей
@app.route('/todo/api/v1.0/users', methods=['GET'])
def get_tasks():
    users = models.User.query.all()
    lt_users = []
    for u in users:
        lt_users.append(user_by_id(u.id))
    return jsonify({'users': lt_users}), 201


# Получить пользователя по id
@app.route('/todo/api/v1.0/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = models.User.query.get(user_id)
    if user is None:
        abort(404)
    return jsonify({'user': user_by_id(user_id)})


# Создание пользователя
@app.route('/todo/api/v1.0/users', methods=['POST'])
def create_user():
    if not request.json or not 'email' in request.json:
        abort(400)
    users = models.User.query.all()
    if users:
        id_user = users[-1].id + 1
    else:
        id_user = 1
    new_user = models.User(
        id=id_user,
        nickname=request.json.get('nickname', ""),
        password=request.json['password'],
        email=request.json['email'],
        role=request.json['role']
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify(user_by_id(id_user)), 201


# Изменение пользователя
@app.route('/todo/api/v1.0/user/<int:user_id>', methods=['PUT'])
# @auth.login_required
def update_user(user_id):
    user = models.User.query.get(user_id)
    if user is None:
        abort(404)
    if not request.json:
        abort(400)
    if 'nickname' in request.json and type(request.json['nickname']) is not unicode:
        abort(400)
    if 'password' in request.json and type(request.json['password']) is not unicode:
        abort(400)
    if 'email' in request.json and type(request.json['email']) is not unicode:
        abort(400)
    if 'role' in request.json and type(request.json['role']) is not unicode:
        abort(400)
    ast = u''
    user.nickname = request.json.get('nickname', user.nickname)
    user.password = request.json.get('password', user.password)
    user.email = request.json.get('email', user.email)
    user.role = request.json.get('role', user.role)
    db.session.commit()
    return jsonify(user_by_id(user_id)), 201, {'Content-Type': 'text/css; charset=utf-8'}


# Удаление пользователя
@app.route('/todo/api/v1.0/users/<int:user_id>', methods=['DELETE'])
# @auth.login_required
def delete_user(user_id):
    user = models.User.query.get(user_id)
    if user is None:
        abort(404)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'result': True})
