# -*- coding: utf-8 -*-

from app import application, models, db
from flask import jsonify, abort, request, make_response, url_for, send_from_directory, render_template
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from config_local import SharedDataMiddleware
from config_local import SERVER_NAME
from functools import wraps
from sqlalchemy import desc
from urllib.parse import unquote
import datetime
import jwt
import sys
import os
import config_local

sys.path.append(config_local.PATH)
from flask_cors import CORS
from sqlalchemy_filters import apply_filters, apply_pagination

auth = HTTPBasicAuth()
application.config['JSON_AS_ASCII'] = False
application.config['UPLOAD_FOLDER'] = config_local.UPLOAD_FOLDER
CORS(application, resources={r"/*": {"origins": "*"}})

application.add_url_rule('/upload/<filename>', 'uploaded_file', build_only=True)
application.wsgi_app = SharedDataMiddleware(application.wsgi_app, {'/upload': application.config['UPLOAD_FOLDER']})
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
@application.errorhandler(404)
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
        suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
        filename = "_".join([suffix, filename])
        file.save(os.path.join(application.config['UPLOAD_FOLDER'], filename))
        return url_for('uploaded_file', filename=filename)


# Формирования словаря полей объявления для json ответа
def ad_by_id(id_elem):
    ad = models.Post.query.get(id_elem)
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
        'price': ad.price,
        'image': SERVER_NAME + ad.image,
        'url': url_for('get_ad', ad_id=ad.id, _external=True),
        'date_create': ad.timestamp,
        'user': ad.user.shops.first().name,
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
            'image': SERVER_NAME + post.image,
            'url': url_for('get_ad', ad_id=post.id, _external=True),
            'user': post.user.shops.first().name
        })
    return jsonify({'ads': user_posts}), 201


# Создание объявления
@application.route('/todo/api/v1.0/ads', methods=['POST'])
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
        active=request.form.get('active', 1),
        model_auto=request.form['model_auto'],
        year_auto=request.form['year_auto'],
        vin_auto=request.form.get('vin_auto', ""),
        price=request.form['price'],
        series=request.form.get('series_auto', ""),
        modification=request.form.get('modification_auto', ""),
        generation=request.form.get('generation_auto', ""),
        fuel=request.form.get('fuel_auto', ""),
        engine=request.form.get('engine_auto', ""),
        user_id=request.form['user_id'],
        image=image_ads,
        timestamp=datetime.datetime.utcnow()
    )
    db.session.add(new_ad)
    db.session.commit()
    return jsonify(ad_by_id(id_ad)), 201


# Изменение объявления
@application.route('/todo/api/v1.0/ads/<int:ad_id>', methods=['PUT'])
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
    ad.fuel = request.form.get('fuel_auto', ad.fuel)
    db.session.commit()
    return jsonify(ad_by_id(ad_id)), 201


# Удаление объявления
@application.route('/todo/api/v1.0/ads/<int:ad_id>', methods=['DELETE'])
# @token_required
def delete_ad(ad_id):
    ad = models.Post.query.get(ad_id)
    if ad is None:
        abort(404)
    if ad.image:
        os.remove(os.path.dirname(os.path.abspath(__file__)) + ad.image)
    db.session.delete(ad)
    db.session.commit()
    return jsonify({'result': True})


# Формирования словаря полей объявления для json ответа
def order_by_id(id_elem):
    order = models.Order.query.get(id_elem)
    d1 = datetime.datetime.strptime(str(order.timestamp), "%Y-%m-%d %H:%M:%S.%f")
    new_format = "%Y-%m-%d %H:%M:%S"
    new_ad_json = {
        'id': order.id,
        'text': order.body,
        'name': order.name,
        'phone': order.phone,
        'email': order.email,
        'shop_id': order.shop_id,
        'url': url_for('get_order', order_id=order.id, _external=True),
        'date_create': d1.strftime(new_format),
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
        d1 = datetime.datetime.strptime(str(order.timestamp), "%Y-%m-%d %H:%M:%S.%f")
        new_format = "%Y-%m-%d %H:%M:%S"
        shop_orders.append({
            'id': order.id,
            'text': order.body,
            'name': order.name,
            'phone': order.phone,
            'email': order.email,
            'shop_id': order.shop_id,
            'url': url_for('get_order', order_id=order.id, _external=True),
            'date_create': d1.strftime(new_format),
            'shop': order.shop.name,
            'ad_id': order.post_id,
            'ad_name': order.post.name_ads,
        })
    return jsonify({'orders': shop_orders}), 201


# Создание заявки
@application.route('/todo/api/v1.0/order', methods=['POST'])
# @token_required
def create_order():
    if not request.form or not 'text' in request.form:
        abort(400)
    order = models.Order.query.all()
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
# @token_required
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
def user_by_id(id_elem):
    user = models.User.query.get(id_elem)
    shop = models.Shop.query.filter_by(user_id=id_elem).first()
    if shop:
        user_shops = {
            'name': shop.name,
            'text': shop.body,
            'phone': shop.phone,
            'city': shop.city,
            'address': shop.address,
            'image': SERVER_NAME + shop.image
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
        city=request.form.get('city', "Иркутск"),
        address=request.form.get('address', "Адрес магазина не заполнен"),
        image=image_shop,
        user_id=id_user
    )
    db.session.add(new_shop)
    db.session.commit()
    return jsonify(user_by_id(id_user)), 201


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
    db.session.commit()
    return jsonify(user_by_id(user_id)), 201


# Удаление пользователя
@application.route('/todo/api/v1.0/users/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(user_id):
    user = models.User.query.get(user_id)
    if user is None:
        abort(404)
    shop = models.Shop.query.filter_by(user_id=user_id).first()
    if shop:
        if shop.image:
            os.remove(os.path.dirname(os.path.abspath(__file__)) + shop.image)
    db.session.delete(shop)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'result': True})


# Авторизация пользователя
@application.route('/todo/api/v1.0/auth', methods=['POST'])
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
                 'shop': {'id': our_user.shops[0].id,
                          'name': our_user.shops[0].name,
                          'text': our_user.shops[0].body,
                          'city': our_user.shops[0].city,
                          'address': our_user.shops[0].address,
                          'phone': our_user.shops[0].phone,
                          'image': SERVER_NAME + our_user.shops[0].image},
                 'url': url_for('get_user', user_id=our_user.id, _external=True),
                 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60)},
                config_local.SECRET_KEY)
            return jsonify({'token': token.decode('UTF-8')}), 201
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
        'image': SERVER_NAME + ad.image,
        'url': url_for('get_ad', ad_id=ad.id, _external=True),
    }
    return new_ad_json


# Получить список марок авто
@application.route('/todo/api/v1.0/auto', methods=['GET'])
# @token_required
def get_auto():
    auto = models.Model.query.all()
    lt_auto = []
    for a in auto:
        lt_auto.append(a.name)
    return jsonify({'auto': lt_auto}), 201


# Получить список модель по марке авто
@application.route('/todo/api/v1.0/auto/<auto_name>', methods=['GET'])
# @token_required
def get_model(auto_name):
    model = db.session.query(models.Model).filter_by(name=unquote(auto_name)).first()
    auto = db.session.query(models.Auto).filter_by(name=model.id).all()
    if auto is None:
        abort(404)
    lt_auto = set()
    for a in auto:
        lt_auto.add(a.model)
    lt_auto = sorted(list(lt_auto))
    return jsonify({'model': lt_auto}), 201


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
    return jsonify({'year': lt_auto}), 201


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
    return jsonify({'series': lt_auto}), 201


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
    return jsonify({'modification': lt_auto}), 201


# Получить топливо по модификации по серии и по году и по модели и марке авто
@application.route('/todo/api/v1.0/auto/<auto_name>/<auto_model>/<auto_year>/<auto_series>/<auto_modification>',
                   methods=['GET'])
# @token_required
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
    return jsonify({'fuel': lt_auto}), 201


@application.route('/')
def get_main_html():
    ads = models.Post.query.order_by(desc(models.Post.id))
    filter_spec = [{'field': 'active', 'op': '==', 'value': 1}]
    filtered_query = apply_filters(ads, filter_spec)
    page = 1
    page_size = 10
    if request.args.get('page'):
        page = int(request.args.get('page'))
    if request.args.get('page_size'):
        page_size = int(request.args.get('page_size'))
    filtered_query, pagination = apply_pagination(filtered_query, page_number=page, page_size=page_size)
    return render_template('main.html', ads=filtered_query, pagination=pagination)


@application.route('/shop/<int:shop_id>')
def get_shop_html(shop_id):
    shop = models.Shop.query.get(shop_id)
    return render_template('shop.html', shop=shop)


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


@application.route('/search')
def get_search_html():
    filter_spec = []
    if request.args.get('mark_auto'):
        filter_spec.append({'field': 'mark_auto', 'op': '==', 'value': request.args.get('mark_auto')})
    if request.args.get('model_auto'):
        filter_spec.append({'field': 'model_auto', 'op': '==', 'value': request.args.get('model_auto')})
    if request.args.get('year_auto'):
        filter_spec.append({'field': 'year_auto', 'op': '==', 'value': request.args.get('year_auto')})
    if request.args.get('series_auto'):
        filter_spec.append({'field': 'series', 'op': '==', 'value': request.args.get('series_auto')})
    if request.args.get('modification_auto'):
        filter_spec.append({'field': 'modification', 'op': '==', 'value': request.args.get('modification_auto')})
    filter_spec.append({'field': 'active', 'op': '==', 'value': 1})
    if request.args.get('name'):
        name_lower = request.args.get('name')
        filter_spec.append({
            'or': [
                {'field': 'name_ads', 'op': 'ilike', 'value': '%' + name_lower + '%'},
                {'field': 'body', 'op': 'ilike', 'value': '%' + name_lower + '%'},
                {'field': 'name_ads', 'op': 'ilike', 'value': '%' + name_lower.lower() + '%'},
                {'field': 'body', 'op': 'ilike', 'value': '%' + name_lower.lower() + '%'},
                {'field': 'name_ads', 'op': 'ilike', 'value': '%' + name_lower.capitalize() + '%'},
                {'field': 'body', 'op': 'ilike', 'value': '%' + name_lower.capitalize() + '%'},
                {'field': 'name_ads', 'op': 'ilike', 'value': '%' + name_lower.upper() + '%'},
                {'field': 'body', 'op': 'ilike', 'value': '%' + name_lower.upper() + '%'},
            ]
        })
    query = models.Post.query
    filtered_query = apply_filters(query, filter_spec)
    page = 1
    page_size = 10
    if request.args.get('page'):
        page = int(request.args.get('page'))
    if request.args.get('page_size'):
        page_size = int(request.args.get('page_size'))
    filtered_query, pagination = apply_pagination(filtered_query, page_number=page, page_size=page_size)
    return render_template('main.html', ads=filtered_query, pagination=pagination)

# Создание объявлений из файла
@application.route('/todo/api/v1.0/csv', methods=['POST'])
# @token_required
def create_ads_from_csv():
    if not request.form:
        abort(400)
    # ads = models.Post.query.all()
    # if ads:
    #     id_ad = ads[-1].id + 1
    # else:
    #     id_ad = 1
    print(request.files['fileex'])
    # if 'file' in request.files:
    #     file = request.files['fileex']
    #     # image_ads = file_to_upload(file)
    # else:
    #     pass
    #     # image_ads = ''
    # print(file)
    # new_ad = models.Post(
    #     id=id_ad,
    #     name_ads=request.form.get('name', ""),
    #     body=request.form.get('text', ""),
    #     mark_auto=request.form['mark_auto'],
    #     active=request.form.get('active', 1),
    #     model_auto=request.form['model_auto'],
    #     year_auto=request.form['year_auto'],
    #     vin_auto=request.form.get('vin_auto', ""),
    #     price=request.form['price'],
    #     series=request.form.get('series_auto', ""),
    #     modification=request.form.get('modification_auto', ""),
    #     generation=request.form.get('generation_auto', ""),
    #     fuel=request.form.get('fuel_auto', ""),
    #     engine=request.form.get('engine_auto', ""),
    #     user_id=request.form['user_id'],
    #     image=image_ads,
    #     timestamp=datetime.datetime.utcnow()
    # )
    # db.session.add(new_ad)
    # db.session.commit()
    return jsonify({'CSV': 'ok'}), 201
