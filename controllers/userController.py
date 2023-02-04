from flask import Blueprint
from services.userService import *

uc = Blueprint('user_controller', __name__, url_prefix='/users')

uc.route('/', methods=['GET'])(get_all_users)
uc.route('/<user_id>', methods=['GET'])(get_user)
uc.route('/signup', methods=['POST'])(signup_user)
uc.route('/login', methods=['POST'])(login_user)