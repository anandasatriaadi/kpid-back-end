from flask import Flask, Blueprint
from flask_cors import CORS
from app.api.user.user_controller import user
from app.api.moderation.moderation_controller import fc
from config import SECRET_KEY
from app.custom_formatter import init_logging;

def create_app():
    init_logging()


    app = Flask(__name__)

    app.config['SECRET_KEY'] = SECRET_KEY

    main = Blueprint('main', __name__, url_prefix='/api')
    main.register_blueprint(user)
    main.register_blueprint(fc)
    app.register_blueprint(main)
    CORS(app)

    @app.route("/ping", methods=["GET"])
    def main():
        return "pong"