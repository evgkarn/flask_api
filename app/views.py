# -*- coding: utf-8 -*-

from app import app, models, db
from flask import jsonify, abort, request, make_response, url_for, send_from_directory, render_template
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from config_local import SharedDataMiddleware
from functools import wraps
from sqlalchemy import desc
import datetime
import jwt
import sys
import os
import config_local

sys.path.append(config_local.PATH)
from flask_cors import CORS
from sqlalchemy_filters import apply_filters

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
        'series_auto': ad.series,
        'modification_auto': ad.modification,
        'generation_auto': ad.generation,
        'fuel_auto': ad.fuel,
        'engine_auto': ad.engine,
        'price': ad.price,
        'image': ad.image,
        'url': url_for('get_ad', ad_id=ad.id, _external=True),
        'date_create': ad.timestamp,
        'user': ad.user.shops.first().name,
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
            'series_auto': post.series,
            'modification_auto': post.modification,
            'generation_auto': post.generation,
            'fuel_auto': post.fuel,
            'engine_auto': post.engine,
            'image': post.image,
            'url': url_for('get_ad', ad_id=post.id, _external=True),
            'user': post.user.shops.first().name
        })
    return jsonify({'ads': user_posts}), 201


# Создание объявления
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
    ad.auto_series = request.form.get('series_auto', ad.auto_series)
    ad.auto_modification = request.form.get('modification_auto', ad.auto_modification)
    ad.generation = request.form.get('generation_auto', ad.generation)
    ad.engine_auto = request.form.get('engine_auto', ad.generation)
    ad.fuel = request.form.get('fuel', ad.fuel)
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
        'series_auto': ad.auto_series,
        'modification_auto': ad.auto_modification,
        'generation_auto': ad.generation,
        'fuel_auto': ad.fuel,
        'engine_auto': ad.engine,
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
    auto = models.Model.query.all()
    lt_auto = set()
    for a in auto:
        lt_auto.add(a.name)
    lt_auto = sorted(list(lt_auto))
    return jsonify({'auto': lt_auto}), 201


# Получить список модель по марке авто
@app.route('/todo/api/v1.0/auto/<auto_name>', methods=['GET'])
# @token_required
def get_model(auto_name):
    model = db.session.query(models.Model).filter_by(name=auto_name).first()
    auto = db.session.query(models.Auto).filter_by(name=model.id).all()
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
    model = db.session.query(models.Model).filter_by(name=auto_name).first()
    auto = db.session.query(models.Auto).filter_by(name=model.id, model=auto_model).all()
    if auto is None:
        abort(404)
    lt_auto = set()
    for a in auto:
        lt_auto.add(a.year)
    lt_auto = sorted(list(lt_auto))
    return jsonify({'year': lt_auto}), 201


# Получить серию по году и по модели и марке авто
@app.route('/todo/api/v1.0/auto/<auto_name>/<auto_model>/<auto_year>', methods=['GET'])
# @token_required
def get_series(auto_name, auto_model, auto_year):
    model = db.session.query(models.Model).filter_by(name=auto_name).first()
    auto = db.session.query(models.Auto).filter_by(name=model.id, model=auto_model, year=auto_year).all()
    if auto is None:
        abort(404)
    lt_auto = set()
    for a in auto:
        lt_auto.add(a.series)
    lt_auto = sorted(list(lt_auto))
    return jsonify({'series': lt_auto}), 201


# Получить модификацию по серии и по году и по модели и марке авто
@app.route('/todo/api/v1.0/auto/<auto_name>/<auto_model>/<auto_year>/<auto_series>', methods=['GET'])
# @token_required
def get_modification(auto_name, auto_model, auto_year, auto_series):
    model = db.session.query(models.Model).filter_by(name=auto_name).first()
    auto = db.session.query(models.Auto).filter_by(name=model.id,
                                                   model=auto_model,
                                                   year=auto_year,
                                                   series=auto_series).all()
    if auto is None:
        abort(404)
    lt_auto = set()
    for a in auto:
        lt_auto.add(a.modification)
    lt_auto = sorted(list(lt_auto))
    return jsonify({'modification': lt_auto}), 201


# Получить топливо по модификации по серии и по году и по модели и марке авто
@app.route('/todo/api/v1.0/auto/<auto_name>/<auto_model>/<auto_year>/<auto_series>/<auto_modification>', methods=['GET'])
# @token_required
def get_fuel(auto_name, auto_model, auto_year, auto_series, auto_modification):
    model = db.session.query(models.Model).filter_by(name=auto_name).first()
    auto = db.session.query(models.Auto).filter_by(name=model.id,
                                                   model=auto_model,
                                                   year=auto_year,
                                                   series=auto_series,
                                                   modification=auto_modification).all()
    if auto is None:
        abort(404)
    lt_auto = set()
    for a in auto:
        lt_auto.add(a.fuel)
    lt_auto = sorted(list(lt_auto))
    return jsonify({'fuel': lt_auto}), 201



@app.route('/')
def get_main_html():
    ads = models.Post.query.order_by(desc(models.Post.id)).all()
    return render_template('main.html', ads=ads)


@app.route('/shop/<int:shop_id>')
def get_shop_html(shop_id):
    shop = models.Shop.query.get(shop_id)
    return render_template('shop.html', shop=shop)


@app.route('/ad/<int:ad_id>')
def get_ad_html(ad_id):
    ad = models.Post.query.get(ad_id)
    recommendation = db.session.query(models.Post).order_by(desc(models.Post.id)).filter_by(mark_auto=ad.mark_auto,
                                                                                            model_auto=ad.model_auto,
                                                                                            year_auto=ad.year_auto).all()
    return render_template('ad.html', ad=ad, recommendation=recommendation)


@app.route('/about')
def get_about_html():
    return render_template('about.html')


@app.route('/partners')
def get_partners_html():
    return render_template('partners.html')


@app.route('/search')
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
    if request.args.get('name'):
        filter_spec.append({
                'or': [
                    {'field': 'name_ads', 'op': 'ilike', 'value': '%'+request.args.get('name')+'%'},
                    {'field': 'body', 'op': 'ilike', 'value': '%'+request.args.get('name')+'%'},
                ]
            })
    query = models.Post.query
    filtered_query = apply_filters(query, filter_spec)
    return render_template('main.html', ads=filtered_query)
