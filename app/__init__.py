from flask import Flask
from flask_cors import CORS

from app.api import api_bp
from app.custom_formatter import init_logging
from config import SECRET_KEY

init_logging()

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.register_blueprint(api_bp, url_prefix='/api')
CORS(app)
