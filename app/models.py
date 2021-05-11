from app import db
from app.search import add_to_index, remove_from_index, query_index

ROLE_USER = 0
ROLE_ADMIN = 1
DEFAULT = ''


class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total['value'] == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):

            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)).filter_by(active=1), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(64), index=True)
    hash_password = db.Column(db.String(120), index=True)
    email = db.Column(db.String(120), index=True, unique=True)
    role = db.Column(db.SmallInteger, default=ROLE_ADMIN)
    status = db.Column(db.String(4), index=True)
    balance = db.Column(db.Integer, index=True)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    shops = db.relationship('Shop', backref='author', lazy='dynamic')

    def __repr__(self):
        return '<User %r>' % self.email


# class Post(db.Model):
class Post(SearchableMixin, db.Model):

    __searchable__ = ['name_ads', 'body', 'mark_auto', 'model_auto', 'year_auto', 'vin_auto', 'price', 'engine', 'generation',
                      'series', 'modification', 'number', 'fuel']
    id = db.Column(db.Integer, primary_key=True, unique=True)
    active = db.Column(db.SmallInteger, default=ROLE_USER)
    name_ads = db.Column(db.String(120), index=True)
    body = db.Column(db.String(768), index=True)
    mark_auto = db.Column(db.String(120), index=True)
    model_auto = db.Column(db.String(120), index=True)
    year_auto = db.Column(db.String(64), index=True)
    vin_auto = db.Column(db.String(64), index=True)
    price = db.Column(db.Integer, index=True)
    image = db.Column(db.String(500), index=True, default=DEFAULT)
    engine = db.Column(db.String(300), index=True, default=DEFAULT)
    generation = db.Column(db.String(200), index=True, default=DEFAULT)
    series = db.Column(db.String(120), index=True, default=DEFAULT)
    modification = db.Column(db.String(120), index=True, default=DEFAULT)
    number = db.Column(db.String(120), index=True, default=DEFAULT)
    left_right = db.Column(db.String(120), index=True, default=DEFAULT)
    front_back = db.Column(db.String(120), index=True, default=DEFAULT)
    up_down = db.Column(db.String(120), index=True, default=DEFAULT)
    quantity = db.Column(db.Integer, index=True)
    fuel = db.Column(db.String(120), index=True, default=DEFAULT)
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User")
    order = db.relationship('Order')

    def __repr__(self):
        return '<Post %r>' % self.name_ads


class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(120), index=True)
    body = db.Column(db.String(768), index=True)
    phone = db.Column(db.String(11), index=True)
    city = db.Column(db.String(400), index=True)
    address = db.Column(db.String(400), index=True)
    image = db.Column(db.String(500), index=True, default=DEFAULT)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User")
    orders = db.relationship('Order')
    pay_orders = db.relationship('PayOrder')
    pay_operation = db.relationship('PayOperation')
    timestamp = db.Column(db.DateTime)

    def __repr__(self):
        return '<Shop %r>' % self.name


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(120), index=True)
    body = db.Column(db.String(768), index=True)
    phone = db.Column(db.String(11), index=True)
    email = db.Column(db.String(120), index=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop")
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    post = db.relationship("Post")
    timestamp = db.Column(db.DateTime)

    def __repr__(self):
        return '<Order %r>' % self.name


class PayOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    status = db.Column(db.SmallInteger, default=ROLE_USER)
    amount = db.Column(db.Integer, index=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop")
    timestamp = db.Column(db.DateTime)

    def __repr__(self):
        return '<PayOrder %r>' % self.id


class PayOperation(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'))
    shop = db.relationship("Shop")
    type = db.Column(db.String(10), index=True)
    amount = db.Column(db.Integer, index=True)
    comment = db.Column(db.String(300), index=True)
    timestamp = db.Column(db.DateTime)

    def __repr__(self):
        return '<PayOperation %r>' % self.id


class Auto(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    id_modification = db.Column(db.Integer, index=True)
    name = db.Column(db.Integer, db.ForeignKey('model.id'))
    model = db.Column(db.String(768), index=True)
    generation = db.Column(db.String(200), index=True)
    year = db.Column(db.Integer, index=True)
    series = db.Column(db.String(120), index=True)
    modification = db.Column(db.String(120), index=True)
    fuel = db.Column(db.String(120), index=True)

    def __repr__(self):
        return '<Auto %r>' % self.name


class Model(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(120), index=True)

    def __repr__(self):
        return '<Model %r>' % self.name


class ModelMark(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    model_id = db.Column(db.Integer, index=True)
    model_name = db.Column(db.String(120), index=True)

    def __repr__(self):
        return '<Model_Mark %r>' % self.model_name


class Rate(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(64), index=True)
    price = db.Column(db.Integer, index=True)
    limit = db.Column(db.Integer, index=True)

    def __repr__(self):
        return '<Name %r>' % self.name
