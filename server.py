from flask import Flask
from exchange import Exchange
from pages import pages
from api import api
from env import DB

app = Flask(__name__)
exchange = Exchange(DB)
pages(app, exchange)
api(app, exchange)
