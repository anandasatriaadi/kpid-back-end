from flask import Flask
from flask_cors import CORS

from app.api import api_bp
from app.custom_formatter import init_logging
from config import SECRET_KEY

# Calling the init_logging function to initialize the logger
init_logging()

# Creating a new Flask application instance
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False
app.register_blueprint(api_bp, url_prefix="/api")
CORS(app)
