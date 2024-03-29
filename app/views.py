# -*- coding: utf-8 -*-
from app import application, models, db
from flask import jsonify, abort, request, make_response, url_for, render_template, send_from_directory
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import NotFound
from config_local import SharedDataMiddleware
from config_local import SERVER_NAME
from functools import wraps
from sqlalchemy import desc
from urllib.parse import unquote
from flask_mail import Mail, Message
from threading import Thread
from PIL import Image
import PIL
import html
import datetime
import jwt
import sys
import os
import config_local
import csv
import requests
import json
import re
import time
import hashlib

sys.path.append(config_local.PATH)


auth = HTTPBasicAuth()
application.config["SQLALCHEMY_POOL_RECYCLE"] = 30
application.config['JSON_AS_ASCII'] = False
application.config['UPLOAD_FOLDER'] = config_local.UPLOAD_FOLDER

application.add_url_rule('/upload/<folder_name>/<filename>', 'uploaded_file', build_only=True)
application.wsgi_app = SharedDataMiddleware(application.wsgi_app, {'/upload': application.config['UPLOAD_FOLDER']})
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'PNG', 'JPG', 'JPEG', 'csv'}

application.config['MAIL_SERVER'] = config_local.MAIL_SERVER
application.config['MAIL_PORT'] = config_local.MAIL_PORT
application.config['MAIL_USE_TLS'] = config_local.MAIL_USE_TLS
application.config['MAIL_USERNAME'] = config_local.MAIL_USERNAME
application.config['MAIL_DEFAULT_SENDER'] = config_local.MAIL_DEFAULT_SENDER
application.config['MAIL_PASSWORD'] = config_local.MAIL_PASSWORD
mail = Mail(application)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.json or 'token' not in request.json:
            if not request.form or 'token' not in request.form:
                if not request.args or 'token' in request.args:
                    abort(400)
                else:
                    token = request.args.get('token')
            else:
                token = request.form.get('token')
        else:
            token = request.json.get('token')
        if not token:
            return jsonify({'message': 'Token is missing'}), 403
        try:
            jwt.decode(token, config_local.SECRET_KEY, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 403

        return f(*args, **kwargs)

    return decorated


# Отправка email
def async_send_mail(app, msg):
    with app.app_context():
        mail.send(msg)


def send_mail(subject, recipient, template, **kwargs):
    msg = Message(subject, sender=application.config['MAIL_DEFAULT_SENDER'], recipients=[recipient])
    msg.html = render_template(template, **kwargs)
    thr = Thread(target=async_send_mail, args=[application, msg])
    thr.start()
    return thr


# Возврат 404 ошибки в json
@application.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


# Проверка на расширения файла
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# Получить расширение файла
def format_file(filename):
    return filename.rsplit('.', 1)[1]


# Путь к файлу по его имени
def path_to_file(name):
    filename = secure_filename(name)
    suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    filename = "_".join([suffix, filename])
    hash_file = hashlib.md5(filename.encode())
    hashed_file = hash_file.hexdigest()
    folder_name = hashed_file[:2]
    if not os.path.exists(os.path.join(application.config['UPLOAD_FOLDER'], folder_name)):
        path = os.path.join(application.config['UPLOAD_FOLDER'], folder_name)
        os.mkdir(path)
    else:
        path = os.path.join(application.config['UPLOAD_FOLDER'], folder_name)
    return filename, folder_name, path


# Функция загрузки фото в папку upload
def file_to_upload(file):
    if file and allowed_file(file.filename):
        filename, folder_name, path = path_to_file(file.filename)
        if format_file(file.filename) != 'csv':
            image = Image.open(file)
            basewidth = 1000
            if image.size[0] > basewidth:
                ratio = (basewidth / float(image.size[0]))
                height = int((float(image.size[1]) * float(ratio)))
                image = image.resize((basewidth, height), PIL.Image.ANTIALIAS)
            image.save(os.path.join(path, filename), quality=80)
        else:
            file.save(os.path.join(path, filename))
        return url_for('uploaded_file', filename=filename, folder_name=folder_name)


# Фукция добавления ордера на оплату
def add_pay_operation(id_order, shop_id, type, amount, comment):
    new_pay_operation = models.PayOperation(
        id=id_order,
        shop_id=shop_id,
        type=type,
        amount=amount,
        comment=comment,
        timestamp=datetime.datetime.utcnow()
    )
    db.session.add(new_pay_operation)
    db.session.commit()
    return "Ok"


# Обновление баланса пользователя
def user_balance(obj_user):
    balance = 0
    for pay in obj_user.shops.first().pay_operation:
        if pay.type == "income":
            balance += pay.amount
        elif pay.type == "expanse":
            balance -= pay.amount
    obj_user.balance = balance
    db.session.commit()


# Тестовое скачиваение файла
@application.route('/todo/api/v1.0/import_file', methods=['POST'])
@token_required
def import_file():
    if 'fileex' in request.files:
        file = request.files['fileex']
        new_file = str(file_to_upload(file))
    else:
        abort(400)
    return jsonify({'file': new_file}), 201


# Формирования словаря полей объявления для json ответа
def ad_by_id(id_elem, error_log=None):
    if error_log is None:
        error_log = {}
    ad = models.Post.query.get(id_elem)
    img = ''
    if ad:
        if ad.image:
            img = SERVER_NAME + ad.image
        new_ad_json = {
            'id': ad.id,
            'user_id': ad.user_id,
            'active': ad.active,
            'name': ad.name_ads,
            'text': ad.body,
            'mark_auto': ad.mark_auto,
            'model_auto': ad.model_auto,
            'year_auto': ad.year_auto,
            'vin_auto': ad.vin_auto,
            'series_auto': ad.series,
            'modification_auto': ad.modification,
            'generation_auto': ad.generation,
            'fuel_auto': ad.fuel,
            'engine_auto': ad.engine,
            'number': ad.number,
            'left_right': ad.left_right,
            'front_back': ad.front_back,
            'up_down': ad.up_down,
            'quantity': ad.quantity,
            'price': ad.price,
            'image': img,
            'url': url_for('get_ad', ad_id=ad.id, _external=True),
            'date_create': ad.timestamp,
            'user': ad.user.shops.first().name,
            'error': error_log
        }
    else:
        new_ad_json = {
            'error': error_log
        }
    return new_ad_json


# Получить все объявления
@application.route('/todo/api/v1.0/ads', methods=['GET'])
# @token_required
def get_ads():
    ads = models.Post.query.all()
    lt_ads = []
    for u in ads:
        lt_ads.append(ad_by_id(u.id))
    return jsonify({'ads': lt_ads}), 201


# Получить объявление по id
@application.route('/todo/api/v1.0/ads/<int:ad_id>', methods=['GET'])
# @token_required
def get_ad(ad_id):
    ad = models.Post.query.get(ad_id)
    if ad is None:
        abort(404)
    return jsonify({'ad': ad_by_id(ad_id)}), 201


# Получить все объявления по id пользователя
@application.route('/todo/api/v1.0/users/<int:user_id>/ads', methods=['GET'])
# @token_required
def get_user_ads(user_id):
    user = models.User.query.get(user_id)
    posts = user.posts
    user_posts = []
    for post in posts:
        img = ''
        if post.image:
            img = SERVER_NAME + post.image
        user_posts.append({
            'name': post.name_ads,
            'text': post.body,
            'active': post.active,
            'mark_auto': post.mark_auto,
            'model_auto': post.model_auto,
            'year_auto': post.year_auto,
            'vin_auto': post.vin_auto,
            'price': post.price,
            'series_auto': post.series,
            'modification_auto': post.modification,
            'generation_auto': post.generation,
            'fuel_auto': post.fuel,
            'engine_auto': post.engine,
            'number': post.number,
            'left_right': post.left_right,
            'front_back': post.front_back,
            'up_down': post.up_down,
            'quantity': post.quantity,
            'image': img,
            'url': url_for('get_ad', ad_id=post.id, _external=True),
            'user': post.user.shops.first().name
        })

    return jsonify({'ads': user_posts}), 201


# Поколения
def async_generation(ad_id):
    thr = Thread(target=generation_search, args=[application, ad_id])
    thr.start()
    return 'Ok'


def generation_search(app, ad_id):
    with app.app_context():
        ad = models.Post.query.get(ad_id)
        if ad is None:
            abort(404)
        filter_spec = dict()
        unique = set()
        if ad.mark_auto:
            mark = models.Model.query.filter_by(name=ad.mark_auto).first()
            filter_spec['name'] = mark.id
        if ad.model_auto:
            filter_spec['model'] = ad.model_auto
        if ad.year_auto:
            filter_spec['year'] = ad.year_auto
        filtered_query = models.Auto.query.filter_by(**filter_spec).all()
        for i in filtered_query:
            unique.add(i.generation)
        unique_list = sorted(list(unique))
        generation_list = ''
        for i in range(len(unique_list)):
            if i + 1 != len(unique_list):
                generation_list += str(unique_list[i]) + ', '
            else:
                generation_list += str(unique_list[i])
        ad.generation = generation_list
        db.session.commit()


# Создание объявления
@application.route('/todo/api/v1.0/ads', methods=['POST'])
@token_required
def create_ads():
    if not request.form or 'text' not in request.form:
        abort(400)
    ads = models.Post.query.order_by(models.Post.id).all()
    user = models.User.query.get(request.form['user_id'])
    rate = models.Rate.query.filter_by(name=user.status).first()
    ad_count = len(user.posts.all())
    if ads:
        id_ad = ads[-1].id + 1
    else:
        id_ad = 1
    if 'file' in request.files:
        file = request.files['file']
        image_ads = file_to_upload(file)
    else:
        image_ads = ''
    error_log = {}
    if ad_count < rate.limit:
        new_ad = models.Post(
            id=id_ad,
            name_ads=request.form.get('name', ""),
            body=request.form.get('text', ""),
            mark_auto=request.form['mark_auto'],
            active=request.form.get('active', 0),
            model_auto=request.form['model_auto'],
            year_auto=request.form['year_auto'],
            vin_auto=request.form.get('vin_auto', ""),
            price=int(request.form['price']),
            series=request.form.get('series_auto', ""),
            modification=request.form.get('modification_auto', ""),
            generation=request.form.get('generation', ""),
            fuel=request.form.get('fuel_auto', ""),
            engine=request.form.get('engine_auto', ""),
            number=request.form.get('number', ""),
            left_right=request.form.get('left_right', ""),
            front_back=request.form.get('front_back', ""),
            up_down=request.form.get('up_down', ""),
            quantity=request.form.get('quantity', 1),
            user_id=int(request.form['user_id']),
            image=image_ads,
            timestamp=datetime.datetime.utcnow(),
            update_timestamp=datetime.datetime.utcnow()
        )
        db.session.add(new_ad)
        db.session.commit()
        async_generation(id_ad)
    else:
        error_log['status'] = 'error'
        error_log['text'] = 'Для текущего тарифа создано максимальное количество объявлений:   ' + str(ad_count)
    return jsonify(ad_by_id(id_ad, error_log)), 201


# Изменение объявления
@application.route('/todo/api/v1.0/ads/<int:ad_id>', methods=['PUT'])
@token_required
def update_ad(ad_id):
    ad = models.Post.query.get(ad_id)
    if ad is None:
        abort(404)
    if not request.form:
        abort(400)
    if 'file' in request.files:
        ad.image = file_to_upload(request.files['file'])
    ad.name_ads = request.form.get('name', ad.name_ads)
    ad.active = request.form.get('active', ad.active)
    ad.body = request.form.get('text', ad.body)
    ad.mark_auto = request.form.get('mark_auto', ad.mark_auto)
    ad.model_auto = request.form.get('model_auto', ad.model_auto)
    ad.year_auto = request.form.get('year_auto', ad.year_auto)
    ad.vin_auto = request.form.get('vin_auto', ad.vin_auto)
    ad.price = request.form.get('price', ad.price)
    ad.series = request.form.get('series_auto', ad.series)
    ad.modification = request.form.get('modification_auto', ad.modification)
    ad.generation = request.form.get('generation_auto', ad.generation)
    ad.engine = request.form.get('engine_auto', ad.engine)
    ad.number = request.form.get('number', ad.number)
    ad.left_right = request.form.get('left_right', ad.left_right)
    ad.front_back = request.form.get('front_back', ad.front_back)
    ad.up_down = request.form.get('up_down', ad.up_down)
    ad.quantity = request.form.get('quantity', ad.quantity)
    ad.fuel = request.form.get('fuel_auto', ad.fuel)
    ad.update_timestamp = datetime.datetime.utcnow()
    db.session.commit()
    async_generation(ad_id)
    return jsonify(ad_by_id(ad_id)), 201


# Удаление объявления
@application.route('/todo/api/v1.0/ads/<int:ad_id>', methods=['DELETE'])
@token_required
def delete_ad(ad_id):
    ad = models.Post.query.get(ad_id)
    if ad is None:
        abort(404)
    if ad.image:
        if os.path.exists(os.path.dirname(os.path.abspath(__file__)) + ad.image):
            os.remove(os.path.dirname(os.path.abspath(__file__)) + ad.image)
    db.session.delete(ad)
    db.session.commit()
    return jsonify({'result': True})


# Формирования словаря полей объявления для json ответа
def order_by_id(id_elem):
    order = models.Order.query.get(id_elem)
    # d1 = datetime.datetime.strptime(str(order.timestamp), "%Y-%m-%d %H:%M:%S.%f")
    new_format = "%Y-%m-%d %H:%M:%S"
    new_ad_json = {
        'id': order.id,
        'text': order.body,
        'name': order.name,
        'phone': order.phone,
        'email': order.email,
        'shop_id': order.shop_id,
        'url': url_for('get_order', order_id=order.id, _external=True),
        'date_create': order.timestamp,
        'shop': order.shop.name,
        'ad_id': order.post.id,
        'ad_name': order.post.name_ads,
    }
    return new_ad_json


# Получить заявку по id
@application.route('/todo/api/v1.0/order/<int:order_id>', methods=['GET'])
# @token_required
def get_order(order_id):
    order = models.Order.query.get(order_id)
    if order is None:
        abort(404)
    return jsonify({'order': order_by_id(order_id)}), 201


# Получить все заявки по id магазина
@application.route('/todo/api/v1.0/shop/<int:shop_id>/orders', methods=['GET'])
# @token_required
def get_order_ads(shop_id):
    shop = models.Shop.query.get(shop_id)
    orders = shop.orders
    shop_orders = []
    for order in orders:
        # d1 = datetime.datetime.strptime(str(order.timestamp), "%Y-%m-%d %H:%M:%S.%f")
        new_format = "%Y-%m-%d %H:%M:%S"
        order_post_id = ''
        order_post_name = 'Объявление удалено'
        if order.post:
            order_post_id = order.post_id,
            order_post_name = order.post.name_ads
        shop_orders.append({
            'id': order.id,
            'text': order.body,
            'name': order.name,
            'phone': order.phone,
            'email': order.email,
            'shop_id': order.shop_id,
            'url': url_for('get_order', order_id=order.id, _external=True),
            'date_create': order.timestamp,
            'shop': order.shop.name,
            'city_id': order.shop.city_shop.city_name,
            'ad_id': order_post_id,
            'ad_name': order_post_name,
        })
    return jsonify({'orders': shop_orders}), 201


# Создание заявки
@application.route('/todo/api/v1.0/order', methods=['POST'])
def create_order():
    if not request.form or 'ad_id' not in request.form:
        abort(400)
    order = models.Order.query.order_by(models.Order.id).all()
    if order:
        id_order = order[-1].id + 1
    else:
        id_order = 1
    new_order = models.Order(
        id=id_order,
        name=request.form.get('name', ""),
        body=request.form.get('text', ""),
        phone=request.form.get('phone', ""),
        email=request.form.get('email', ""),
        shop_id=request.form['shop_id'],
        post_id=request.form['ad_id'],
        timestamp=datetime.datetime.utcnow()
    )
    db.session.add(new_order)
    db.session.commit()
    return jsonify(order_by_id(id_order)), 201


# Изменение заявки
@application.route('/todo/api/v1.0/order/<int:order_id>', methods=['PUT'])
@token_required
def update_order(order_id):
    order = models.Order.query.get(order_id)
    if order is None:
        abort(404)
    if not request.form:
        abort(400)
    order.name = request.form.get('name', order.name)
    order.body = request.form.get('text', order.body)
    order.phone = request.form.get('phone', order.phone)
    order.email = request.form.get('email', order.email)
    db.session.commit()
    return jsonify(order_by_id(order_id)), 201


# Формирования словаря полей пользователя для json ответа
def user_by_id(id_elem, error_log=None):
    if error_log is None:
        error_log = {}
    user = models.User.query.get(id_elem)
    shop = models.Shop.query.filter_by(user_id=id_elem).first()
    user_shops = {}
    token = {}
    img = ''
    if shop.image:
        img = SERVER_NAME + shop.image
    if shop:
        user_shops = {
            'name': shop.name,
            'text': shop.body,
            'phone': shop.phone,
            'city': shop.city,
            'address': shop.address,
            'image': img
        }
        token = jwt.encode(
            {'user': user.email,
             'id': user.id,
             'role': user.role,
             'status': user.status,
             'balance': user.balance / 100,
             'ads': url_for('get_user_ads', user_id=user.id, _external=True),
             'shop': {'id': shop.id,
                      'name': shop.name,
                      'text': shop.body,
                      'city': shop.city,
                      'address': shop.address,
                      'phone': shop.phone,
                      'image': img},
             'url': url_for('get_user', user_id=user.id, _external=True),
             'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60)},
            config_local.SECRET_KEY, algorithm="HS256")
    new_user_json = {
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'status': user.status,
        'balance': user.balance / 100,
        'url': url_for('get_user', user_id=user.id, _external=True),
        'error': error_log
    }
    user_posts = models.Post.query.filter_by(user_id=id_elem).first()
    if user_posts:
        new_user_json['ads'] = url_for('get_user_ads', user_id=user.id, _external=True)
    if shop:
        new_user_json['shop'] = user_shops
    if token:
        new_user_json['token'] = token.encode().decode('UTF-8')
    return new_user_json


# Получить всех пользователей
@application.route('/todo/api/v1.0/users', methods=['GET'])
# @token_required
def get_users():
    users = models.User.query.all()
    lt_users = []
    for u in users:
        lt_users.append(user_by_id(u.id))
    return jsonify({'users': lt_users}), 201


# Получить пользователя по id
@application.route('/todo/api/v1.0/users/<int:user_id>', methods=['GET'])
# @token_required
def get_user(user_id):
    user = models.User.query.get(user_id)
    if user is None:
        abort(404)
    return jsonify({'user': user_by_id(user_id)}), 201


# Создание пользователя
@application.route('/todo/api/v1.0/users', methods=['POST'])
def create_user():
    if not request.form or 'email' not in request.form:
        abort(400)
    our_user = db.session.query(models.User).filter_by(email=request.form['email']).first()
    if our_user is not None:
        return jsonify({'error': 'User already created'})
    users = models.User.query.order_by(models.User.id).all()
    if users:
        id_user = users[-1].id + 1
    else:
        id_user = 1
    new_user = models.User(
        id=id_user,
        hash_password=generate_password_hash((request.form['password'])),
        email=request.form['email'],
        role=request.form['role'],
        status=request.form.get('status', 'free'),
        balance=0
    )
    db.session.add(new_user)
    db.session.commit()
    shop = models.Shop.query.order_by(models.Shop.id).all()
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
        name=request.form.get('name_shop', 'Тут должно быть название магазина'),
        body=request.form.get('text_shop', "Описание магазина не заполнено"),
        phone=request.form.get('phone', ''),
        city=request.form.get('city', 'Иркутск'),
        city_id=request.form.get('city_id', 1),
        address=request.form.get('address', 'Адрес магазина не заполнен'),
        image=image_shop,
        user_id=id_user,
        date_create=datetime.datetime.utcnow(),
        date_change_status=datetime.datetime.utcnow()
    )
    db.session.add(new_shop)
    db.session.commit()
    send_mail("Данные при регистрации на Azato.ru", request.form['email'], "mail/new_user.html", login=request.form['email'],
              password=request.form['password'])
    return jsonify(user_by_id(id_user)), 201


# Изменение тарифа пользователя
def change_status(user, status):
    error_log = {'status': 'OK', 'text': "Тариф изменён"}
    rate = models.Rate.query.filter_by(name=status).first()
    if not rate:
        abort(400)
    if status == user.status:
        error_log['status'] = 'error'
        error_log['text'] = 'Выбранный тариф равен текущему'
    elif rate.price * 100 > user.balance:
        error_log['status'] = 'error'
        error_log['text'] = 'Недостаточно средств на балансе'
    elif error_log['status'] != 'error':
        active_ads = user.posts.filter_by(active=1).all()
        if len(active_ads) > rate.limit:
            for ad in active_ads[:len(active_ads) - rate.limit]:
                ad.active = 0
            error_log['status'] = 'OK'
            error_log['text'] = 'Количество активных объявлений после изменения тарифа: ' + str(
                rate.limit)
        pay_operation = models.PayOperation.query.order_by(models.PayOperation.id).all()
        if pay_operation:
            id_order = pay_operation[-1].id + 1
        else:
            id_order = 1
        add_pay_operation(id_order, user.shops.first().id, 'expanse', rate.price * 100, status)
        user.status = status
        user.shops.first().date_change_status = datetime.datetime.utcnow()
        db.session.commit()
        if user.shops.first().pay_operation:
            user_balance(user)
    return error_log


# Изменение пользователя
@application.route('/todo/api/v1.0/users/<int:user_id>', methods=['PUT'])
@token_required
def update_user(user_id):
    user = models.User.query.get(user_id)
    if user is None:
        abort(404)
    if not request.form:
        abort(400)
    if 'password' in request.form:
        user.hash_password = generate_password_hash(request.form['password'])
    error_log = {'status': 'OK', 'text': None}
    if 'status' in request.form:
        error_log = change_status(user, request.form['status'])
    user.email = request.form.get('email', user.email)
    user.role = request.form.get('role', user.role)
    shop = models.Shop.query.filter_by(user_id=user_id).first()
    if shop:
        if 'file' in request.files:
            shop.image = file_to_upload(request.files['file'])
        shop.name = request.form.get('name_shop', shop.name)
        shop.body = request.form.get('text_shop', shop.body)
        shop.phone = request.form.get('phone', shop.phone)
        shop.city = request.form.get('city', shop.city)
        shop.address = request.form.get('address', shop.address)
        shop.city_id = request.form.get('city_id', shop.city_shop.id)
    db.session.commit()
    return jsonify(user_by_id(user_id, error_log)), 201


# Удаление пользователя
@application.route('/todo/api/v1.0/users/<int:user_id>', methods=['DELETE'])
# @token_required
def delete_user(user_id):
    user = models.User.query.get(user_id)
    if user is None:
        abort(404)
    delete_ads_users(user_id)
    shop = models.Shop.query.filter_by(user_id=user_id).first()
    if shop:
        if shop.image:
            if os.path.exists(os.path.dirname(os.path.abspath(__file__)) + shop.image):
                os.remove(os.path.dirname(os.path.abspath(__file__)) + shop.image)
        if shop.pay_operation:
            for operation in shop.pay_operation:
                db.session.delete(operation)
        if shop.pay_orders:
            for pay_order in shop.pay_orders:
                db.session.delete(pay_order)
        if shop.orders:
            for order in shop.orders:
                db.session.delete(order)
        db.session.delete(shop)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'result': True})


# Удаление всех объявление пользователя
@application.route('/todo/api/v1.0/ads_delete/<int:user_id>', methods=['DELETE'])
# @token_required
def delete_ads_users(user_id):
    ads = models.Post.query.filter_by(user_id=user_id).all()
    if ads is None:
        abort(404)
    for ad in ads:
        if ad.image:
            if os.path.exists(os.path.dirname(os.path.abspath(__file__)) + ad.image):
                os.remove(os.path.dirname(os.path.abspath(__file__)) + ad.image)
        db.session.delete(ad)
    db.session.commit()
    return jsonify({'result': True})


# Активация деактивация объявлений
@application.route('/todo/api/v1.0/ads_active/<int:user_id>', methods=['PUT'])
@token_required
def active_ads_users(user_id):
    if not request.form or 'active' not in request.form:
        abort(400)
    if request.form['active'] != '0' and request.form['active'] != '1':
        abort(400)
    ads = models.Post.query.filter_by(user_id=user_id).all()
    if ads is None:
        abort(404)
    for ad in ads:
        ad.active = int(request.form['active'])
        ad.update_timestamp = datetime.datetime.utcnow()
    db.session.commit()
    return jsonify({'result': True})


# Авторизация пользователя
@application.route('/todo/api/v1.0/auth', methods=['POST'])
def auth_user():
    if not request.json or 'email' not in request.json:
        abort(400)
    if not request.json or 'password' not in request.json:
        abort(400)
    our_user = db.session.query(models.User).filter_by(email=request.json['email']).first()
    img = ''
    if our_user.shops[0].image:
        img = SERVER_NAME + our_user.shops[0].image
    if our_user is not None:
        if check_password_hash(our_user.hash_password, request.json['password']):
            token = jwt.encode(
                {'user': our_user.email,
                 'id': our_user.id,
                 'role': our_user.role,
                 'status': our_user.status,
                 'balance': our_user.balance / 100,
                 'ads': url_for('get_user_ads', user_id=our_user.id, _external=True),
                 'shop': {'id': our_user.shops[0].id,
                          'name': our_user.shops[0].name,
                          'text': our_user.shops[0].body,
                          'city_id': our_user.shops[0].city_shop.city_name,
                          'address': our_user.shops[0].address,
                          'phone': our_user.shops[0].phone,
                          'image': img},
                 'url': url_for('get_user', user_id=our_user.id, _external=True),
                 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60)},
                config_local.SECRET_KEY, algorithm="HS256")
            return jsonify({'token': token.encode().decode('UTF-8')}), 201
        else:
            return jsonify({'error': 'Unauthorized access'})
    else:
        return jsonify({'error': 'Unknown user'})


@application.route('/todo/api/v1.0/auth', methods=['GET', 'PUT', 'DELETE'])
def auth_user_get():
    return make_response(jsonify({'error': 'Not found'}), 404)


# Формирования словаря полей объявления для json ответа
def shop_by_id(id_elem):
    ad = models.Shop.query.get(id_elem)
    img = ''
    if ad.image:
        img = SERVER_NAME + ad.image
    new_ad_json = {
        'id': ad.id,
        'user_id': ad.user_id,
        'name': ad.name_ads,
        'text': ad.body,
        'active': ad.active,
        'mark_auto': ad.mark_auto,
        'model_auto': ad.model_auto,
        'year_auto': ad.year_auto,
        'series_auto': ad.auto_series,
        'modification_auto': ad.auto_modification,
        'generation_auto': ad.generation,
        'fuel_auto': ad.fuel,
        'engine_auto': ad.engine,
        'vin_auto': ad.vin_auto,
        'price': ad.price,
        'number': ad.number,
        'left_right': ad.left_right,
        'front_back': ad.front_back,
        'up_down': ad.up_down,
        'quantity': ad.quantity,
        'image': img,
        'url': url_for('get_ad', ad_id=ad.id, _external=True),
    }
    return new_ad_json


# Формирования словаря полей города для json ответа
def city_by_id(id_city):
    city = models.City.query.get(id_city)
    new_city_json = {
        'id': city.id,
        'name': city.city_name,
        'domain': city.city_domain,
    }
    return new_city_json


# Создание города
@application.route('/todo/api/v1.0/city', methods=['POST'])
@token_required
def create_city():
    if not request.form or 'name' not in request.form:
        abort(400)
    city = models.City.query.order_by(models.City.id).all()
    if city:
        id_city = city[-1].id + 1
    else:
        id_city = 1
    new_city = models.City(
        id=id_city,
        city_name=request.form.get('name', ""),
        city_domain=request.form.get('domain', ""),
    )
    db.session.add(new_city)
    db.session.commit()
    return jsonify(city_by_id(id_city)), 201


# Получить все города
@application.route('/todo/api/v1.0/city', methods=['GET'])
# @token_required
def get_cities():
    cities = models.City.query.all()
    lt_cities = []
    for u in cities:
        lt_cities.append(city_by_id(u.id))
    return jsonify({'cities': lt_cities}), 201


# Получить город по id
@application.route('/todo/api/v1.0/city/<int:id_city>', methods=['GET'])
# @token_required
def get_city(id_city):
    city = models.City.query.get(id_city)
    if city is None:
        abort(404)
    return jsonify({'city': city_by_id(id_city)}), 201


# Удаление города
@application.route('/todo/api/v1.0/city/<int:id_city>', methods=['DELETE'])
@token_required
def delete_city(id_city):
    city = models.City.query.get(id_city)
    if city is None:
        abort(404)
    db.session.delete(city)
    db.session.commit()
    return jsonify({'result': True})


# Получить список марок авто
@application.route('/todo/api/v1.0/auto', methods=['GET'])
# @token_required
def get_auto():
    auto = models.Model.query.all()
    lt_auto = []
    for a in auto:
        lt_auto.append(a.name)
    return jsonify({'auto': lt_auto})


# Получить список модель по марке авто (если пустая, возвращает полный массив с данными марка-модели)
@application.route('/todo/api/v1.0/auto/<auto_name>', methods=['GET'])
# @token_required
def get_model(auto_name):
    if auto_name != "all":
        model = db.session.query(models.Model).filter_by(name=unquote(auto_name)).first()
        if model is None:
            abort(404)
        auto = db.session.query(models.Auto).filter_by(name=model.id).all()
        if auto is None:
            abort(404)
        lt_auto = set()
        for a in auto:
            lt_auto.add(a.model)
        lt_auto = sorted(list(lt_auto))
        return jsonify({'model': lt_auto})
    else:
        model = db.session.query(models.Model).all()
        all_m = dict()
        for m in model:
            mark_auto = db.session.query(models.ModelMark).filter_by(model_id=m.id).all()
            lt_auto = set()
            for a in mark_auto:
                lt_auto.add(a.model_name)
            lt_auto = sorted(list(lt_auto))
            all_m[m.name] = lt_auto
        return jsonify(all_m)


# Получить год по модели и марке авто
@application.route('/todo/api/v1.0/auto/<auto_name>/<auto_model>', methods=['GET'])
# @token_required
def get_year(auto_name, auto_model):
    model = db.session.query(models.Model).filter_by(name=unquote(auto_name)).first()
    auto = db.session.query(models.Auto).filter_by(name=model.id, model=unquote(auto_model)).all()
    if auto is None:
        abort(404)
    lt_auto = set()
    for a in auto:
        lt_auto.add(a.year)
    lt_auto = sorted(list(lt_auto))
    return jsonify({'year': lt_auto})


# Получить серию по году и по модели и марке авто
@application.route('/todo/api/v1.0/auto/<auto_name>/<auto_model>/<auto_year>', methods=['GET'])
# @token_required
def get_series(auto_name, auto_model, auto_year):
    model = db.session.query(models.Model).filter_by(name=unquote(auto_name)).first()
    auto = db.session.query(models.Auto).filter_by(name=model.id, model=unquote(auto_model),
                                                   year=unquote(auto_year)).all()
    if auto is None:
        abort(404)
    lt_auto = set()
    for a in auto:
        lt_auto.add(a.series)
    lt_auto = sorted(list(lt_auto))
    return jsonify({'series': lt_auto})


# Получить модификацию по серии и по году и по модели и марке авто
@application.route('/todo/api/v1.0/auto/<auto_name>/<auto_model>/<auto_year>/<auto_series>', methods=['GET'])
# @token_required
def get_modification(auto_name, auto_model, auto_year, auto_series):
    model = db.session.query(models.Model).filter_by(name=unquote(auto_name)).first()
    auto = db.session.query(models.Auto).filter_by(name=model.id,
                                                   model=unquote(auto_model),
                                                   year=unquote(auto_year),
                                                   series=unquote(auto_series)).all()
    if auto is None:
        abort(404)
    lt_auto = set()
    for a in auto:
        lt_auto.add(a.modification)
    lt_auto = sorted(list(lt_auto))
    return jsonify({'modification': lt_auto})


# Получить топливо по модификации по серии и по году и по модели и марке авто
@application.route('/todo/api/v1.0/auto/<auto_name>/<auto_model>/<auto_year>/<auto_series>/<auto_modification>',
                   methods=['GET'])
@token_required
def get_fuel(auto_name, auto_model, auto_year, auto_series, auto_modification):
    model = db.session.query(models.Model).filter_by(name=unquote(auto_name)).first()
    auto = db.session.query(models.Auto).filter_by(name=model.id,
                                                   model=unquote(auto_model),
                                                   year=unquote(auto_year),
                                                   series=unquote(auto_series),
                                                   modification=unquote(auto_modification)).all()
    if auto is None:
        abort(404)
    lt_auto = set()
    for a in auto:
        lt_auto.add(a.fuel)
    lt_auto = sorted(list(lt_auto))
    return jsonify({'fuel': lt_auto})


@application.route('/', methods=['GET'], defaults={"page": 1})
@application.route('/<int:page>', methods=['GET'])
def get_main_html(page):
    page = page
    per_page = 10
    ads = models.Post.query.order_by(desc(models.Post.id)).filter_by(active=1).paginate(page, per_page, error_out=False)
    return render_template('main.html', ads=ads)


@application.route('/shop/<int:shop_id>')
def get_shop_html(shop_id):
    shop = models.Shop.query.get(shop_id)
    per_page = 10
    page = request.args.get('page', 1, type=int)
    ads = models.Post.query.order_by(desc(models.Post.id)).filter_by(
        active=1,
        user_id=shop.user_id
    ).paginate(page, per_page, error_out=False)
    total = {'value': ads.total}
    if total != 0:
        if total['value'] % per_page == 0:
            pages = total['value'] // per_page
        else:
            pages = (total['value'] // per_page) + 1
    else:
        total = {'value': 0}
        pages = 0
    url = re.sub(r'.page=\d+', '', request.url)
    if len(request.args) == 1 and request.args.get('page') or not request.args:
        url += '?'
    else:
        url += '&'
    args = request.args
    return render_template('shop.html', ads=ads, pagination=total, this_page=page, pages=pages,
                           url=url,
                           args=args,
                           shop=shop)


@application.route('/ad/<int:ad_id>')
def get_ad_html(ad_id):
    ad = db.session.query(models.Post).order_by(desc(models.Post.id)).filter_by(id=ad_id, active=1).first()
    if ad is None:
        abort(404)
    recommendation = db.session.query(models.Post).order_by(desc(models.Post.id)).filter_by(mark_auto=ad.mark_auto,
                                                                                            model_auto=ad.model_auto,
                                                                                            year_auto=ad.year_auto,
                                                                                            active=1).all()
    return render_template('ad.html', ad=ad, recommendation=recommendation)


@application.route('/about')
def get_about_html():
    return render_template('about.html')


@application.route('/partners')
def get_partners_html():
    return render_template('partners.html')


@application.route('/oferta')
def get_oferta_html():
    return render_template('oferta.html')


# Скачивание файла объявлений
@application.route('/todo/api/v1.0/import_csv_file', methods=['POST'])
@token_required
def import_csv_file():
    file_path = config_local.APP_FOLDER
    if 'fileex' in request.files:
        file = request.files['fileex']
        new_file = str(file_to_upload(file))
        file_path += new_file
    else:
        abort(400)
    return jsonify({'file': new_file}), 201


# Создание объявлений из файла
@application.route('/todo/api/v1.0/csv', methods=['POST'])
@token_required
def create_ads_from_csv():
    ads = models.Post.query.order_by(models.Post.id).all()
    if ads:
        id_ad = ads[-1].id
    else:
        id_ad = 1
    file_path = config_local.APP_FOLDER
    if 'user_id' not in request.form:
        abort(400)
    if 'file_name' in request.form:
        file = request.form['file_name']
        file_path += file
    else:
        abort(400)
    ads = []
    error_log = []
    user = models.User.query.get(request.form['user_id'])
    rate = models.Rate.query.filter_by(name=user.status).first()
    ad_count = len(user.posts.all())
    if ad_count >= rate.limit:
        error_log.append({
            'number_row': 1,
            'field': 'Превышен лимит объявлений',
            'text_error': 'Создано максимальное количество объявлений по тарифу: ' + str(
                user.status) + '. Максимум: ' + str(rate.limit) + ' объявлений.'
        })
        result = {'Всего строк': 0,
                  'Загружено': 0,
                  'Ошибки': error_log
                  }
        return jsonify(result), 201
    if os.path.isfile(file_path):
        with open(file_path, newline="", encoding='windows-1251') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            count = 0
            res_mark = json.loads(get_auto().get_data().decode("utf-8"))
            res_model = json.loads(get_model("all").get_data().decode("utf-8"))
            for row in reader:
                if count < rate.limit:
                    id_ad += 1
                    if row['Название объявления']:
                        row['Название объявления'] = html.escape(row['Название объявления'])
                    else:
                        error_log.append({
                            'number_row': count,
                            'field': row['Название объявления'],
                            'text_error': 'Поле должно быть заполнено'
                        })
                        continue
                    if row['Текст объявления']:
                        row['Текст объявления'] = html.escape(row['Текст объявления'])
                    else:
                        error_log.append({
                            'number_row': count,
                            'field': row['Текст объявления'],
                            'text_error': 'Поле должно быть заполнено'
                        })
                        continue
                    if row['Марка авто']:
                        if row['Марка авто'].lower() not in res_mark['auto']:
                            error_log.append({
                                'number_row': count,
                                'field': row['Марка авто'],
                                'text_error': 'Марка авто должна строго соответствовать существующим значениям в базе данных. См. руководство.'
                            })
                    else:
                        error_log.append({
                            'number_row': count,
                            'field': row['Марка авто'],
                            'text_error': 'Марка авто должна строго соответствовать существующим значениям в базе данных. См. руководство.'
                        })
                        continue
                    if row['Модель Авто']:
                        try:
                            res_model[row['Марка авто'].lower()]
                        except KeyError:
                            error_log.append({
                                'number_row': count,
                                'field': row['Модель Авто'].lower(),
                                'text_error': 'Модель авто должна строго соответствовать существующим значениям в базе данных. См. руководство.'
                            })
                            continue
                        if row['Модель Авто'].lower() not in res_model[row['Марка авто'].lower()]:
                            error_log.append({
                                'number_row': count,
                                'field': row['Модель Авто'].lower(),
                                'text_error': 'Модель авто должна строго соответствовать существующим значениям в базе данных. См. руководство.'
                            })
                            continue
                    else:
                        error_log.append({
                            'number_row': count,
                            'field': row['Модель Авто'],
                            'text_error': 'Модель авто должна строго соответствовать существующим значениям в базе данных. См. руководство.'
                        })
                        continue
                    if row['Год']:
                        row['Год'] = html.escape(row['Год'])
                    else:
                        row['Год'] = ''
                    if row['Кузов']:
                        row['Кузов'] = html.escape(row['Кузов'])
                    else:
                        row['Кузов'] = ''
                    if not row['Цена'].isdigit():
                        error_log.append({
                            'number_row': count,
                            'field': row['Цена'],
                            'text_error': 'Цена должна быть строго из цифр. См. руководство.'
                        })
                        continue
                    if row['Двигатель']:
                        row['Двигатель'] = html.escape(row['Двигатель'])
                    else:
                        row['Двигатель'] = ''
                    if row['Номер']:
                        row['Номер'] = html.escape(row['Номер'])
                    else:
                        row['Номер'] = ''
                    if row['Left-Right']:
                        row['Left-Right'] = html.escape(row['Left-Right'])
                    else:
                        row['Left-Right'] = ''
                    if row['Front-Back']:
                        row['Front-Back'] = html.escape(row['Front-Back'])
                    else:
                        row['Front-Back'] = ''
                    if row['Up-Down']:
                        row['Up-Down'] = html.escape(row['Up-Down'])
                    else:
                        row['Up-Down'] = ''
                    if row['Количество'] and not row['Количество'].isdigit():
                        error_log.append({
                            'number_row': count,
                            'field': row['Количество'],
                            'text_error': 'Количество должен строго состоять из цифр. См. руководство.'
                        })
                        continue
                    else:
                        row['Количество'] = ''
                    # if row['Фотография'] and allowed_file(row['Фотография']):
                    if row['Фотография']:
                        try:
                            img = row['Фотография']
                        except requests.exceptions.ConnectionError:
                            error_log.append({
                                'number_row': count,
                                'field': row['Фотография'],
                                'text_error': 'Фотография по ссылке не доступна.'
                            })
                            img = ''
                    else:
                        error_log.append({
                            'number_row': count,
                            'field': row['Фотография'],
                            'text_error': 'Не корректная ссылка на фотографию'
                        })
                        img = ''
                    ads.append({
                        'id': id_ad,
                        'name_ads': row['Название объявления'],
                        'body': row['Текст объявления'],
                        'mark_auto': row['Марка авто'].lower(),
                        'model_auto': row['Модель Авто'].lower(),
                        'year_auto': row['Год'],
                        'vin_auto': row['Кузов'],
                        'price': row['Цена'],
                        'image': img,
                        'engine': row['Двигатель'],
                        'number': row['Номер'],
                        'left_right': row['Left-Right'],
                        'front_back': row['Front-Back'],
                        'up_down': row['Up-Down'],
                        'quantity': row['Количество']
                    })
                    count += 1
                else:
                    break
    count_res = 0
    ad_count = len(user.posts.all())
    for ad in ads:
        if ad_count < rate.limit:
            count_res += 1
            # if ad['image'] and allowed_file(ad['image']):
            if ad['image']:
                img = requests.get(ad['image']).content
                suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S%f")
                filename = "_".join([suffix, 'upload_img.jpg'])
                filename, folder_name, path = path_to_file(filename)
                out = open(os.path.join(path, filename), "wb")
                out.write(img)
                out.close()
                image_path = url_for('uploaded_file', filename=filename, folder_name=folder_name)
            else:
                image_path = ''
            id_ad += 1
            new_ad = models.Post(
                id=ad['id'],
                active=0,
                name_ads=ad['name_ads'],
                body=ad['body'],
                mark_auto=ad['mark_auto'],
                model_auto=ad['model_auto'],
                year_auto=ad['year_auto'],
                vin_auto=ad['vin_auto'],
                generation=request.form.get('generation', ""),
                price=int(ad['price']),
                user_id=int(request.form['user_id']),
                image=image_path,
                timestamp=datetime.datetime.utcnow()
            )
            db.session.add(new_ad)
            ad_count += 1
        else:
            error_log.append({
                'number_row': count,
                'field': 'Превышен лимит объявлений',
                'text_error': 'Создано максимальное количество объявлений по тарифу: ' + str(
                    user.status) + '. Максимум: ' + str(rate.limit) + 'объявлений.'
            })
            break
    db.session.commit()
    for ad in ads:
        async_generation(ad['id'])
    os.remove(file_path)
    result = {'Всего строк обработано по тарифу': count,
              'Корректных': len(ads),
              'Ошибки': error_log,
              'Загружено с учётом лимита по тарифу': count_res
              }
    return jsonify(result), 201


# Формирования словаря полей объявления для json ответа
def pay_by_id(id_elem):
    order = models.PayOrder.query.get(id_elem)
    # d1 = datetime.datetime.strptime(str(order.timestamp), "%Y-%m-%d %H:%M:%S.%f")
    new_format = "%Y-%m-%d %H:%M:%S"
    new_pay_json = {
        'id': order.id,
        'amount': order.amount / 100,
        'shop_id': order.shop_id,
        'date_create': order.timestamp,
    }
    return new_pay_json


# Создание заказа на оплату и получение ссылки
@application.route('/todo/api/v1.0/pay', methods=['POST'])
@token_required
def create_pay():
    if not request.form or 'shop_id' not in request.form:
        abort(400)
    amount = 0
    if request.form['amount']:
        amount = int(request.form['amount']) * 100
    order = models.PayOrder.query.order_by(models.PayOrder.id).all()
    if order:
        id_order = order[-1].id + 1
    else:
        id_order = 1
    new_order = models.PayOrder(
        id=id_order,
        status=0,
        amount=amount,
        shop_id=request.form['shop_id'],
        timestamp=datetime.datetime.utcnow()
    )
    db.session.add(new_order)
    db.session.commit()
    order = models.PayOrder.query.get(id_order)
    # d1 = datetime.datetime.strptime(str(order.timestamp), "%Y-%m-%d %H:%M:%S.%f")
    new_format = "%Y-%m-%d %H:%M:%S"

    # Отправка запроса в банк
    url = 'https://securepay.tinkoff.ru/v2/Init'
    headers = {'Content-type': 'application/json',
               'Accept': 'text/plain',
               'Content-Encoding': 'utf-8'}
    data = {
        "TerminalKey": config_local.TERMINAL_KEY,
        "Amount": order.amount,
        "OrderId": order.id,
        "DATA": {
            "Phone": order.shop.phone,
            "Email": order.shop.user.email
        },
        "Receipt": {
            "EmailCompany": "sale@azato.ru",
            "Taxation": "usn_income",
            "Phone": order.shop.phone,
            "Email": order.shop.user.email,
            "Items": [
                {
                    "Name": "Размещение объявления",
                    "Price": order.amount,
                    "Quantity": 1.00,
                    "Amount": order.amount,
                    "PaymentMethod": "full_prepayment",
                    "PaymentObject": "service",
                    "Tax": "none"
                }
            ]
        }
    }
    answer = requests.post(url, data=json.dumps(data), headers=headers)
    response = answer.json()
    pay_json = {
        'id': order.id,
        'amount': order.amount / 100,
        'shop_id': order.shop_id,
        'date_create': order.timestamp,
        'Payment': response
    }
    return jsonify(pay_json), 201


# Подтверждение оплаты
@application.route('/todo/api/v1.0/pay_status', methods=['POST'])
def status_pay():
    if not request.json['Success'] is True:
        abort(400)
    order = models.PayOrder.query.get(request.json['OrderId'])
    if order is None:
        abort(400)
    pay_operation = models.PayOperation.query.order_by(models.PayOperation.id).all()
    if pay_operation:
        id_order = pay_operation[-1].id + 1
    else:
        id_order = 1
    if request.json['Status'] == "CONFIRMED":
        add_pay_operation(id_order, order.shop_id, 'income', request.json.get('Amount', 0), request.json['Status'])
        order.status = 1
    if request.json['Status'] == "REFUNDED":
        add_pay_operation(id_order, order.shop_id, 'expanse', request.json.get('Amount', 0), request.json['Status'])
        order.status = 0
    if request.json['Status'] == "PARTIAL_REFUNDED":
        add_pay_operation(id_order, order.shop_id, 'expanse', request.json.get('Amount', 0), request.json['Status'])
        order.status = 1
    db.session.commit()
    if order.shop.pay_operation:
        user_balance(order.shop.user)
    return make_response("OK", 200)


@application.route('/search', methods=['GET'])
def search():
    qsearch = ''
    filters = {'active': 1}
    args = request.args
    if request.args.get('name'):
        qsearch += request.args.get('name')
        if request.args.get('model_auto'):
            if request.args.get('model_auto') != 'all':
                filters['model_auto'] = request.args.get('model_auto').lower()
        if request.args.get('mark_auto'):
            if request.args.get('mark_auto') != 'all':
                filters['mark_auto'] = request.args.get('mark_auto').lower()
        if request.args.get('year_auto'):
            if request.args.get('year_auto') != 'all':
                filter_year = dict()
                unique = set()
                generation_list = ''
                if request.args.get('mark_auto'):
                    mark = models.Model.query.filter_by(name=request.args.get('mark_auto').lower()).first()
                    filter_year['name'] = mark.id
                if request.args.get('model_auto'):
                    filter_year['model'] = request.args.get('model_auto').lower()
                if request.args.get('year_auto'):
                    filter_year['year'] = request.args.get('year_auto')
                    filtered_query_year = models.Auto.query.filter_by(**filter_year).all()
                    for i in filtered_query_year:
                        unique.add(i.generation)
                    unique_list = sorted(list(unique))
                    for i in range(len(unique_list)):
                        if i + 1 != len(unique_list):
                            generation_list += str(unique_list[i]) + ', '
                        else:
                            generation_list += str(unique_list[i])
                filters['generation'] = generation_list
        elem_list = 10
        page = request.args.get('page', 1, type=int)
        posts, total = models.Post.search(qsearch, page, elem_list, filters)
        if total != 0:
            if total['value'] % elem_list == 0:
                pages = total['value'] // elem_list
            else:
                pages = (total['value'] // elem_list) + 1
        else:
            total = {'value': 0}
            pages = 0
        url = re.sub(r'.page=\d+', '', request.url)
        if len(request.args) == 1 and request.args.get('page') or not request.args:
            url += '?'
        else:
            url += '&'
    else:
        per_page = 10
        page = request.args.get('page', 1, type=int)
        if request.args.get('model_auto'):
            if request.args.get('model_auto') != 'all':
                filters['model_auto'] = request.args.get('model_auto').lower()
        if request.args.get('mark_auto'):
            if request.args.get('mark_auto') != 'all':
                filters['mark_auto'] = request.args.get('mark_auto').lower()
        if request.args.get('year_auto'):
            if request.args.get('year_auto') != 'all':
                filter_year = dict()
                unique = set()
                generation_list = ''
                if request.args.get('mark_auto'):
                    mark = models.Model.query.filter_by(name=request.args.get('mark_auto').lower()).first()
                    filter_year['name'] = mark.id
                if request.args.get('model_auto'):
                    filter_year['model'] = request.args.get('model_auto').lower()
                if request.args.get('year_auto'):
                    filter_year['year'] = request.args.get('year_auto')
                    filtered_query_year = models.Auto.query.filter_by(**filter_year).all()
                    for i in filtered_query_year:
                        unique.add(i.generation)
                    unique_list = sorted(list(unique))
                    for i in range(len(unique_list)):
                        if i + 1 != len(unique_list):
                            generation_list += str(unique_list[i]) + ', '
                        else:
                            generation_list += str(unique_list[i])
                filters['generation'] = generation_list
        posts = models.Post.query.order_by(desc(models.Post.id)).filter_by(**filters).paginate(page,
                                                                                               per_page,
                                                                                               error_out=False)
        total = {'value': posts.total}
        posts = posts.items
        if total != 0:
            if total['value'] % per_page == 0:
                pages = total['value'] // per_page
            else:
                pages = (total['value'] // per_page) + 1
        else:
            total = {'value': 0}
            pages = 0
        url = re.sub(r'.page=\d+', '', request.url)
        if len(request.args) == 1 and request.args.get('page') or not request.args:
            url += '?'
        else:
            url += '&'
    return render_template('search_new.html', ads=posts, pagination=total, this_page=page, pages=pages, search=qsearch,
                           url=url,
                           args=args)


# Переиндексация поиска
@application.route('/todo/api/v1.0/reindex', methods=['GET'])
# @token_required
def reindex_search():
    models.Post.reindex()
    return jsonify({'Reindex': 'true'}), 201


# Вывод файла ads.txt для проверки рекламы
@application.route('/ads.txt')
def ads():
    return send_from_directory(application.static_folder, request.path[1:])
