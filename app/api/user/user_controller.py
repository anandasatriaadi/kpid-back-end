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
    # Parse query parameters from the request
    params = {"_id": None}
    params["page"] = request.args.get('page', default=0, type=int)
    params["limit"] = request.args.get('limit', default=10, type=int)
    sort = request.args.get('sort', default='_id,ASC')
    params["sort_field"], params["sort_order"] = sort.split(',')

    # Call the get_user_by_params function with the parsed query parameters and return the response
    return get_user_by_params(params)


# ======== get user by token ========
@user_bp.route('/user', methods=['GET'])
@token_required
def get_user(current_user):
    response = BaseResponse()

    # Convert the current user data to a UserResponse object
    current_user = from_dict(data_class=UserResponse, data=current_user)

    # Set the response data to the current user and return the response
    response.set_response(current_user, HTTPStatus.OK)
    return response.get_response()


# ======== signup user ========
@user_bp.route('/signup', methods=['POST'])
def signup():
    # Parse the request data based on its MIME type
    if request.mimetype == "application/json":
        user_data = from_dict(
            data_class=CreateUserRequest, data=request.get_json())
    else:
        user_data = from_dict(data_class=CreateUserRequest, data=request.form)

    # Call the signup_user function to create a new user account
    return signup_user(user_data)


# ======== login user ========
@user_bp.route('/login', methods=['POST'])
def login():
    # Parse the request data based on its MIME type
    if request.mimetype == "application/json":
        user_data = from_dict(
            data_class=LoginUserRequest, data=request.get_json())
    else:
        user_data = from_dict(data_class=LoginUserRequest, data=request.form)

    # Call the login_user function to authenticate the user and generate a JWT
    return login_user(user_data)
