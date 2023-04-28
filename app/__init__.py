from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from elasticsearch import Elasticsearch

application = Flask(__name__, static_folder='static', static_url_path='')
CORS(application, resources={r"/*": {"origins": "*"}})
application.config.from_object('config')
db = SQLAlchemy(application)
from app import views
import config_local

application.elasticsearch = Elasticsearch([config_local.ELASTICSEARCH_URL]) \
    if config_local.ELASTICSEARCH_URL else None



