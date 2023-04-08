import logging
from http import HTTPStatus

from dacite import from_dict
from flask import Blueprint, request

from app.api.common.utils import token_required
from app.api.user.user_service import (get_user_by_params, login_user,
                                       signup_user)
from app.dto import (BaseResponse, CreateUserRequest, LoginUserRequest,
                     UserResponse)

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)


# ======== get all users ========
@user_bp.route('/users', methods=['GET'])
@token_required
def get_all_users(_):
    params = {"_id": None}
    params["page"] = request.args.get('page', default=0, type=int)
    params["limit"] = request.args.get('limit', default=10, type=int)
    sort = request.args.get('sort', default='_id,ASC')
    params["sort_field"], params["sort_order"] = sort.split(',')

    return get_user_by_params(params)


# ======== get user by token ========
@user_bp.route('/user', methods=['GET'])
@token_required
def get_user(current_user):
    response = BaseResponse()
    current_user = from_dict(data_class=UserResponse, data=current_user)
    response.set_response(current_user, HTTPStatus.OK)
    return response.get_response()


# ======== signup user ========
@user_bp.route('/signup', methods=['POST'])
def signup():
    if request.mimetype == "application/json":
        user_data = from_dict(
            data_class=CreateUserRequest, data=request.get_json())
    else:
        user_data = from_dict(data_class=CreateUserRequest, data=request.form)

    print(user_data.__dict__)

    return signup_user(user_data)


# ======== login user ========
@user_bp.route('/login', methods=['POST'])
def login():
    if request.mimetype == "application/json":
        user_data = from_dict(
            data_class=LoginUserRequest, data=request.get_json())
    else:
        user_data = from_dict(data_class=LoginUserRequest, data=request.form)

    return login_user(user_data)
