import logging
from http import HTTPStatus

from dacite import from_dict
from flask import Blueprint, request

from app.api.common.wrapper_utils import is_admin, token_required
from app.api.user.user_service import (
    aggregate_user_login,
    get_user_by_params,
    login_user,
    signup_user,
    update_user,
)
from app.dto import (
    BaseResponse,
    CreateUserRequest,
    LoginUserRequest,
    UpdateUserRequest,
    User,
    UserResponse,
)

logger = logging.getLogger(__name__)
user_bp = Blueprint("user", __name__)


# ======== get all users ========
@user_bp.route("/users", methods=["GET"])
@token_required
@is_admin
def get_all_users(_):
    # Parse query parameters from the request
    params = {}
    params["page"] = request.args.get("page", default=0, type=int)
    params["limit"] = request.args.get("limit", default=20, type=int)
    params["sort"] = request.args.get("sort", default="_id,ASC")
    params["is_active"] = request.args.get("is_active", default=True)

    # Call the get_user_by_params function with the parsed query parameters and return the response
    return get_user_by_params(params)


# ======== get user by token ========
@user_bp.route("/users/<user_id>", methods=["GET"])
@token_required
def get_user(current_user: User, user_id: str):
    response = BaseResponse()
    if str(current_user._id) == user_id:
        # Convert the current user data to a UserResponse object
        current_user = from_dict(data_class=UserResponse, data=current_user.as_dict())

        # Set the response data to the current user and return the response
        response.set_response(current_user, HTTPStatus.OK)
        return response.get_response()
    else:
        response.set_response("Unauthorized", HTTPStatus.UNAUTHORIZED)
        return response.get_response()


# ======== signup user ========
@user_bp.route("/users/signup", methods=["POST"])
def signup():
    # Parse the request data based on its MIME type
    try:
        if request.mimetype == "application/json":
            user_data = from_dict(data_class=CreateUserRequest, data=request.get_json())
        else:
            user_data = from_dict(data_class=CreateUserRequest, data=request.form)
    except Exception as err:
        logger.error(err)
        response = BaseResponse()
        response.set_response("Bad Request", HTTPStatus.BAD_REQUEST)
        return response.get_response()

    # Call the signup_user function to create a new user account
    return signup_user(user_data)


# ======== login user ========
@user_bp.route("/users/login", methods=["POST"])
def login():
    try:
        # Parse the request data based on its MIME type
        if request.mimetype == "application/json":
            user_data = from_dict(data_class=LoginUserRequest, data=request.get_json())
        else:
            user_data = from_dict(data_class=LoginUserRequest, data=request.form)
    except Exception as err:
        logger.error(err)
        response = BaseResponse()
        response.set_response("Bad Request", HTTPStatus.BAD_REQUEST)
        return response.get_response()

    # Call the login_user function to authenticate the user and generate a JWT
    return login_user(user_data)


# ======== update user ========
@user_bp.route("/users", methods=["PUT"])
@token_required
def update_user_data(current_user: User):
    try:
        if request.mimetype == "application/json":
            user_data = UpdateUserRequest(
                user_id=current_user._id,
                name=request.get_json().get("name"),
                email=request.get_json().get("email"),
            )
        else:
            user_data = UpdateUserRequest(
                user_id=current_user._id,
                name=request.form.get("name"),
                email=request.form.get("email"),
            )
    except Exception as err:
        logger.error(err)
        response = BaseResponse()
        response.set_response("Bad Request", HTTPStatus.BAD_REQUEST)
        return response.get_response()

    return update_user(user_data)


# ======== delete user ========
@user_bp.route("/users/<user_id>", methods=["DELETE"])
@token_required
@is_admin
def delete_user(current_user: User, user_id: str):
    response = BaseResponse()
    if str(current_user._id) == user_id:
        response.set_response("Cannot delete current user", HTTPStatus.BAD_REQUEST)
        return response.get_response()

    user_data = UpdateUserRequest(user_id, is_active=False)

    return update_user(user_data)


# ======== update user's role ========
@user_bp.route("/users/role", methods=["PUT"])
@token_required
@is_admin
def update_user_role(current_user: User):
    try:
        if request.mimetype == "application/json":
            user_data = UpdateUserRequest(
                user_id=request.get_json().get("user_id"),
                role=request.get_json().get("role"),
            )
        else:
            user_data = UpdateUserRequest(
                user_id=request.form.get("user_id"), role=request.form.get("role")
            )
    except Exception as err:
        logger.error(err)
        response = BaseResponse()
        response.set_response("Bad Request", HTTPStatus.BAD_REQUEST)
        return response.get_response()

    return update_user(user_data)


# ======== update user's role ========
@user_bp.route("/users/test", methods=["get"])
@token_required
def test(current_user: User):
    return aggregate_user_login()
