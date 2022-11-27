from flask import Flask
from flask_cors import CORS
from controllers.userController import uc
from controllers.formController import fc
from config import SECRET_KEY
from utils.CustomFormatter import init_logging;

init_logging()

app = Flask(__name__)

app.config['SECRET_KEY'] = SECRET_KEY

app.register_blueprint(uc, url_prefix='/api')
app.register_blueprint(fc, url_prefix='/api')
CORS(app)

if __name__ == "__main__":
    app.run(debug = True)
