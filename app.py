from flask import Flask
from controllers.userController import uc
from config import SECRET_KEY
from utils.CustomFormatter import init_logging;

init_logging()

app = Flask(__name__)

app.config['SECRET_KEY'] = SECRET_KEY

app.register_blueprint(uc, url_prefix='/api')

if __name__ == "__main__":
    app.run(debug = True)