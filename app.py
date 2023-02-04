from flask import Flask, Blueprint
from flask_cors import CORS
from controllers.userController import uc
from controllers.formController import fc
from config import SECRET_KEY
from utils.CustomFormatter import init_logging;

init_logging()

app = Flask(__name__)

app.config['SECRET_KEY'] = SECRET_KEY

main = Blueprint('main', __name__, url_prefix='/api')
main.register_blueprint(uc)
main.register_blueprint(fc)
app.register_blueprint(main)
CORS(app)

@app.route("/ping")
def main():
	return "pong"

if __name__ == "__main__":
    app.run(debug = True)
