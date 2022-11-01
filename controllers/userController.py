from flask import Blueprint
from services.userService import *

uc = Blueprint('user_controller', __name__)

uc.route('/userinfo', methods=['GET'])(get_all_users)
uc.route('/signup', methods=['POST'])(signup_user)
uc.route('/login', methods=['POST'])(login_user)