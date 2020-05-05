# -*- coding: utf-8 -*-
from numpy import unicode
from app import app, models, db
from flask import jsonify, abort, request, make_response, url_for
from flask_httpauth import HTTPBasicAuth
import datetime
import sys

sys.path.append('/home/evgkarn/.virtualenvs/my-venv/lib/python3.6/site-packages')
from flask_cors import CORS

auth = HTTPBasicAuth()
app.config['JSON_AS_ASCII'] = False
CORS(app)


@auth.get_password
def get_password(username):
    if username == 'miguel':
        return 'python'
    return None


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 403)


# Формирования словаря полей объявления для json ответа
def ad_by_id(id_elem):
    ad = models.Post.query.get(id_elem)
    new_ad_json = {
        'id': ad.id,
        'user_id': ad.user_id,
        'name': ad.name_ads,
        'text': ad.body,
        'mark_auto': ad.mark_auto,
        'model_auto': ad.model_auto,
        'year_auto': ad.year_auto,
        'vin_auto': ad.vin_auto,
        'price': ad.price,
        'url': url_for('get_ad', ad_id=ad.id, _external=True),
        'date_create': ad.timestamp
    }
    return new_ad_json


# Получить все объявления
@app.route('/todo/api/v1.0/ads', methods=['GET'])
def get_ads():
    ads = models.Post.query.all()
    lt_ads = []
    for u in ads:
        lt_ads.append(ad_by_id(u.id))
    return jsonify({'ads': lt_ads}), 201


# Получить объявление по id
@app.route('/todo/api/v1.0/ads/<int:ad_id>', methods=['GET'])
def get_ad(ad_id):
    ad = models.Post.query.get(ad_id)
    if ad is None:
        abort(404)
    return jsonify({'ad': ad_by_id(ad_id)}), 201


# Возврат 404 ошибки в json
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


# Cоздание объявления
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
        user_id=request.json['user_id'],
        timestamp=datetime.datetime.utcnow()
    )
    db.session.add(new_ad)
    db.session.commit()
    return jsonify(ad_by_id(id_ad)), 201


# Изменение объявления
@app.route('/todo/api/v1.0/ads/<int:ad_id>', methods=['PUT'])
# @auth.login_required
def update_ad(ad_id):
    ad = models.Post.query.get(ad_id)
    if ad is None:
        abort(404)
    if not request.json:
        abort(400)
    if 'name' in request.json and type(request.json['name']) is not unicode:
        abort(400)
    if 'text' in request.json and type(request.json['text']) is not unicode:
        abort(400)
    if 'mark_auto' in request.json and type(request.json['mark_auto']) is not unicode:
        abort(400)
    if 'model_auto' in request.json and type(request.json['model_auto']) is not unicode:
        abort(400)
    if 'year_auto' in request.json and type(request.json['year_auto']) is not unicode:
        abort(400)
    if 'vin_auto' in request.json and type(request.json['vin_auto']) is not unicode:
        abort(400)
    if 'price' in request.json and type(request.json['price']) is not unicode:
        abort(400)
    ad.name_ads = request.json.get('name', ad.name_ads)
    ad.body = request.json.get('text', ad.body)
    ad.mark_auto = request.json.get('mark_auto', ad.mark_auto)
    ad.model_auto = request.json.get('model_auto', ad.model_auto)
    ad.year_auto = request.json.get('year_auto', ad.year_auto)
    ad.vin_auto = request.json.get('vin_auto', ad.vin_auto)
    ad.price = request.json.get('price', ad.price)
    db.session.commit()
    return jsonify(ad_by_id(ad_id)), 201


# Удаление объявления
@app.route('/todo/api/v1.0/ads/<int:ad_id>', methods=['DELETE'])
# @auth.login_required
def delete_ad(ad_id):
    ad = models.Post.query.get(ad_id)
    if ad is None:
        abort(404)
    db.session.delete(ad)
    db.session.commit()
    return jsonify({'result': True})


# Формирования словаря полей пользователя для json ответа
def user_by_id(id_elem):
    user = models.User.query.get(id_elem)
    posts = user.posts
    user_posts = []
    for post in posts:
        user_posts.append({
            'name': post.name_ads,
            'text': post.body,
            'mark_auto': post.mark_auto,
            'model_auto': post.model_auto,
            'year_auto': post.year_auto,
            'vin_auto': post.vin_auto,
            'price': post.price,
            'url': url_for('get_ad', ad_id=post.id, _external=True)
        })
    new_user_json = {
        'id': user.id,
        'nickname': user.nickname,
        'password': user.password,
        'email': user.email,
        'role': user.role,
        'url': url_for('get_user', user_id=user.id, _external=True),
        'ads': user_posts
    }
    return new_user_json


# Получить всех пользователей
@app.route('/todo/api/v1.0/users', methods=['GET'])
def get_users():
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
    return jsonify({'user': user_by_id(user_id)}), 201


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
    user.nickname = request.json.get('nickname', user.nickname)
    user.password = request.json.get('password', user.password)
    user.email = request.json.get('email', user.email)
    user.role = request.json.get('role', user.role)
    db.session.commit()
    return jsonify(user_by_id(user_id)), 201


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


# Авторизация пользователя
@app.route('/todo/api/v1.0/auth', methods=['POST'])
def auth_user():
    if not request.json or not 'email' in request.json:
        abort(400)
    if not request.json or not 'password' in request.json:
        abort(400)
    our_user = db.session.query(models.User).filter_by(email=request.json['email']).first()
    if our_user is not None:
        if our_user.password == request.json['password']:
            user_auth = {
                'nickname': our_user.nickname,
                'email': our_user.email,
                'role': our_user.role,
                'url': url_for('get_user', user_id=our_user.id, _external=True),
            }
            return jsonify({'user': user_auth}), 201
        else:
            return jsonify({'error': 'Unauthorized access'})
    else:
        return jsonify({'error': 'Unknown user'})
