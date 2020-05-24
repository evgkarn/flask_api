from app import db

ROLE_USER = 0
ROLE_ADMIN = 1


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(64), index=True)
    hash_password = db.Column(db.String(120), index=True)
    email = db.Column(db.String(120), index=True, unique=True)
    role = db.Column(db.SmallInteger, default=ROLE_USER)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    shops = db.relationship('Shop', backref='author', lazy='dynamic')

    def __repr__(self):
        return '<User %r>' % self.nickname


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name_ads = db.Column(db.String(120), index=True)
    body = db.Column(db.String(768), index=True)
    mark_auto = db.Column(db.String(120), index=True)
    model_auto = db.Column(db.String(120), index=True)
    year_auto = db.Column(db.String(64), index=True)
    vin_auto = db.Column(db.String(64), index=True)
    price = db.Column(db.Integer, index=True)
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post %r>' % self.nameads


class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(120), index=True)
    body = db.Column(db.String(768), index=True)
    phone = db.Column(db.Integer, index=True)
    address = db.Column(db.String(400), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Shop %r>' % self.name


class Auto(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(120), index=True)
    model = db.Column(db.String(768), index=True)
    year = db.Column(db.Integer, index=True)

    def __repr__(self):
        return '<Auto %r>' % self.name
