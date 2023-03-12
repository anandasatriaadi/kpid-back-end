from app.api.user import user
from app.api.user.user_service import (get_all_users, get_user, login_user,
                                       signup_user)

user.route('/users', methods=['GET'])(get_all_users)
user.route('/user', methods=['GET'])(get_user)
user.route('/signup', methods=['POST'])(signup_user)
user.route('/login', methods=['POST'])(login_user)
