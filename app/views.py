# -*- coding: utf-8 -*-
from app import app, models, db
from flask import jsonify, abort, request, make_response, url_for, send_from_directory
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from config_local import SharedDataMiddleware
from functools import wraps
import datetime
import jwt
import sys
import os
import config_local

sys.path.append(config_local.PATH)
from flask_cors import CORS

auth = HTTPBasicAuth()
app.config['JSON_AS_ASCII'] = False
app.config['UPLOAD_FOLDER'] = config_local.UPLOAD_FOLDER
CORS(app, resources={r"/*": {"origins": "*"}})

app.add_url_rule('/upload/<filename>', 'uploaded_file', build_only=True)
app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {'/upload': app.config['UPLOAD_FOLDER']})
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.json or not 'token' in request.json:
            if not request.form or not 'token' in request.form:
                abort(400)
            else:
                token = request.form.get('token')
        else:
            token = request.json.get('token')
        if not token:
            return jsonify({'message': 'Token is missing'}), 403
        try:
            data = jwt.decode(token, config_local.SECRET_KEY)
        except:
            return jsonify({'message': 'Token is invalid!'}), 403

        return f(*args, **kwargs)

    return decorated


# Возврат 404 ошибки в json
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


# Проверка на расширения файла
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# Функция загруки фото в папку upload
def file_to_upload(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return url_for('uploaded_file', filename=filename, _external=True)


# Загрузка фото
@app.route('/todo/api/v1.0/upload', methods=['GET', 'POST'])
def upload_file():
    if 'file' in request.files:
        file = request.files['file']
        return jsonify({'image': file_to_upload(file)}), 201
    else:
        abort(404)


@app.route('/todo/api/v1.0/upload/<filename>', methods=['GET'])
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


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
        'image': ad.image,
        'url': url_for('get_ad', ad_id=ad.id, _external=True),
        'date_create': ad.timestamp
    }
    return new_ad_json


# Получить все объявления
@app.route('/todo/api/v1.0/ads', methods=['GET'])
# @token_required
def get_ads():
    ads = models.Post.query.all()
    lt_ads = []
    for u in ads:
        lt_ads.append(ad_by_id(u.id))
    return jsonify({'ads': lt_ads}), 201


# Получить объявление по id
@app.route('/todo/api/v1.0/ads/<int:ad_id>', methods=['GET'])
# @token_required
def get_ad(ad_id):
    ad = models.Post.query.get(ad_id)
    if ad is None:
        abort(404)
    return jsonify({'ad': ad_by_id(ad_id)}), 201


# Получить все объявления по id пользователя
@app.route('/todo/api/v1.0/users/<int:user_id>/ads', methods=['GET'])
# @token_required
def get_user_ads(user_id):
    user = models.User.query.get(user_id)
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
            'image': post.image,
            'url': url_for('get_ad', ad_id=post.id, _external=True)
        })
    return jsonify({'ads': user_posts}), 201


# Cоздание объявления
@app.route('/todo/api/v1.0/ads', methods=['POST'])
# @token_required
def create_ads():
    if not request.form or not 'text' in request.form:
        abort(400)
    ads = models.Post.query.all()
    if ads:
        id_ad = ads[-1].id + 1
    else:
        id_ad = 1
    if 'file' in request.files:
        file = request.files['file']
        image_ads = file_to_upload(file)
    else:
        image_ads = ''
    new_ad = models.Post(
        id=id_ad,
        name_ads=request.form.get('name', ""),
        body=request.form.get('text', ""),
        mark_auto=request.form['mark_auto'],
        model_auto=request.form['model_auto'],
        year_auto=request.form['year_auto'],
        vin_auto=request.form['vin_auto'],
        price=request.form['price'],
        user_id=request.form['user_id'],
        image=image_ads,
        timestamp=datetime.datetime.utcnow()
    )
    db.session.add(new_ad)
    db.session.commit()
    return jsonify(ad_by_id(id_ad)), 201


# Изменение объявления
@app.route('/todo/api/v1.0/ads/<int:ad_id>', methods=['PUT'])
# @token_required
def update_ad(ad_id):
    ad = models.Post.query.get(ad_id)
    if ad is None:
        abort(404)
    if not request.form:
        abort(400)
    if 'file' in request.files:
        ad.image = file_to_upload(request.files['file'])
    ad.name_ads = request.form.get('name', ad.name_ads)
    ad.body = request.form.get('text', ad.body)
    ad.mark_auto = request.form.get('mark_auto', ad.mark_auto)
    ad.model_auto = request.form.get('model_auto', ad.model_auto)
    ad.year_auto = request.form.get('year_auto', ad.year_auto)
    ad.vin_auto = request.form.get('vin_auto', ad.vin_auto)
    ad.price = request.form.get('price', ad.price)
    db.session.commit()
    return jsonify(ad_by_id(ad_id)), 201


# Удаление объявления
@app.route('/todo/api/v1.0/ads/<int:ad_id>', methods=['DELETE'])
# @token_required
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
    shop = models.Shop.query.filter_by(user_id=id_elem).first()
    if shop:
        user_shops = {
            'name': shop.name,
            'text': shop.body,
            'phone': shop.phone,
            'address': shop.address,
            'image': shop.image
        }
    new_user_json = {
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'url': url_for('get_user', user_id=user.id, _external=True)
    }
    user_posts = models.Post.query.filter_by(user_id=id_elem).first()
    if user_posts:
        new_user_json['ads'] = url_for('get_user_ads', user_id=user.id, _external=True)
    if shop:
        new_user_json['shop'] = user_shops
    return new_user_json


# Получить всех пользователей
@app.route('/todo/api/v1.0/users', methods=['GET'])
# @token_required
def get_users():
    users = models.User.query.all()
    lt_users = []
    for u in users:
        lt_users.append(user_by_id(u.id))
    return jsonify({'users': lt_users}), 201


# Получить пользователя по id
@app.route('/todo/api/v1.0/users/<int:user_id>', methods=['GET'])
# @token_required
def get_user(user_id):
    user = models.User.query.get(user_id)
    if user is None:
        abort(404)
    return jsonify({'user': user_by_id(user_id)}), 201


# Создание пользователя
@app.route('/todo/api/v1.0/users', methods=['POST'])
def create_user():
    if not request.form or not 'email' in request.form:
        abort(400)
    our_user = db.session.query(models.User).filter_by(email=request.form['email']).first()
    if our_user is not None:
        return jsonify({'error': 'User already created'})
    users = models.User.query.all()
    if users:
        id_user = users[-1].id + 1
    else:
        id_user = 1
    new_user = models.User(
        id=id_user,
        hash_password=generate_password_hash((request.form['password'])),
        email=request.form['email'],
        role=request.form['role']
    )
    db.session.add(new_user)
    db.session.commit()
    shop = models.Shop.query.all()
    if shop:
        id_shop = shop[-1].id + 1
    else:
        id_shop = 1
    if 'file' in request.files:
        file = request.files['file']
        image_shop = file_to_upload(file)
    else:
        image_shop = ''
    new_shop = models.Shop(
        id=id_shop,
        name=request.form['name_shop'],
        body=request.form.get('text_shop', "Описание магазина не заполнено"),
        phone=request.form['phone'],
        address=request.form.get('address', "Адрес магазина не заполнен"),
        image=image_shop,
        user_id=id_user
    )
    db.session.add(new_shop)
    db.session.commit()
    return jsonify(user_by_id(id_user)), 201


# Изменение пользователя
@app.route('/todo/api/v1.0/users/<int:user_id>', methods=['PUT'])
@token_required
def update_user(user_id):
    user = models.User.query.get(user_id)
    if user is None:
        abort(404)
    if not request.form:
        abort(400)
    if 'password' in request.form:
        user.hash_password = generate_password_hash(request.form['password'])
    user.email = request.form.get('email', user.email)
    user.role = request.form.get('role', user.role)
    shop = models.Shop.query.filter_by(user_id=user_id).first()
    if shop:
        if 'file' in request.files:
            shop.image = file_to_upload(request.files['file'])
        shop.name = request.form.get('name_shop', shop.name)
        shop.body = request.form.get('text_shop', shop.body)
        shop.phone = request.form.get('phone', shop.phone)
        shop.address = request.form.get('address', shop.address)
    db.session.commit()
    return jsonify(user_by_id(user_id)), 201


# Удаление пользователя
@app.route('/todo/api/v1.0/users/<int:user_id>', methods=['DELETE'])
@token_required
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
        if check_password_hash(our_user.hash_password, request.json['password']):
            token = jwt.encode(
                {'user': our_user.email,
                 'id': our_user.id,
                 'role': our_user.role,
                 'ads': url_for('get_user_ads', user_id=our_user.id, _external=True),
                 'shop': {'name': our_user.shops[0].name,
                          'text': our_user.shops[0].body,
                          'address': our_user.shops[0].address,
                          'phone': our_user.shops[0].phone,
                          'image': our_user.shops[0].image},
                 'url': url_for('get_user', user_id=our_user.id, _external=True),
                 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
                config_local.SECRET_KEY)
            return jsonify({'token': token.decode('UTF-8')}), 201
        else:
            return jsonify({'error': 'Unauthorized access'})
    else:
        return jsonify({'error': 'Unknown user'})


@app.route('/todo/api/v1.0/auth', methods=['GET', 'PUT', 'DELETE'])
def auth_user_get():
    return make_response(jsonify({'error': 'Not found'}), 404)


# Формирования словаря полей объявления для json ответа
def shop_by_id(id_elem):
    ad = models.Shop.query.get(id_elem)
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
        'image': ad.image,
        'url': url_for('get_ad', ad_id=ad.id, _external=True),
    }
    return new_ad_json


# Получить список марок авто
@app.route('/todo/api/v1.0/auto', methods=['GET'])
# @token_required
def get_auto():
    auto = models.Auto.query.all()
    lt_auto = set()
    for a in auto:
        lt_auto.add(a.name)
    lt_auto = sorted(list(lt_auto))
    return jsonify({'auto': lt_auto}), 201


# Получить список модель по марке авто
@app.route('/todo/api/v1.0/auto/<auto_name>', methods=['GET'])
# @token_required
def get_model(auto_name):
    auto = db.session.query(models.Auto).filter_by(name=auto_name).all()
    if auto is None:
        abort(404)
    lt_auto = set()
    for a in auto:
        lt_auto.add(a.model)
    lt_auto = sorted(list(lt_auto))
    return jsonify({'model': lt_auto}), 201


# Получить год по модели и марке авто
@app.route('/todo/api/v1.0/auto/<auto_name>/<auto_model>', methods=['GET'])
# @token_required
def get_year(auto_name, auto_model):
    auto = db.session.query(models.Auto).filter_by(name=auto_name, model=auto_model).all()
    if auto is None:
        abort(404)
    lt_auto = set()
    for a in auto:
        lt_auto.add(a.year)
    lt_auto = sorted(list(lt_auto))
    return jsonify({'year': lt_auto}), 201
