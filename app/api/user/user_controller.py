from flask import Blueprint

from app.api.user.user_service import (get_all_users, get_user, login_user,
                                       signup_user)

user_bp = Blueprint('user', __name__)

user_bp.route('/users', methods=['GET'])(get_all_users)
user_bp.route('/user', methods=['GET'])(get_user)
user_bp.route('/signup', methods=['POST'])(signup_user)
user_bp.route('/login', methods=['POST'])(login_user)
