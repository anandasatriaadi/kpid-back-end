import logging
from http import HTTPStatus

from dacite import from_dict
from flask import Blueprint, request

from app.api.common.wrapper_utils import is_admin, token_required
from app.api.exceptions import ApplicationException
from app.api.user.user_service import (
    get_user_by_params,
    login_user,
    signup_user,
    update_user,
)
from app.dto import (
    BaseResponse,
    CreateUserRequest,
    LoginUserRequest,
    PaginateResponse,
    UpdateUserRequest,
    User,
    UserResponse,
)

logger = logging.getLogger(__name__)
user_bp = Blueprint("user", __name__)


# get all users
@user_bp.route("/users", methods=["GET"])
@token_required
@is_admin
def get_all_users(_):
    response = PaginateResponse()

    try:
        # Parse query parameters from the request
        params = {}
        params["page"] = request.args.get("page", default=0, type=int)
        params["limit"] = request.args.get("limit", default=20, type=int)
        params["sort"] = request.args.get("sort", default="_id,ASC")
        params["is_active"] = request.args.get("is_active", default=True)

        # Call the get_user_by_params function with the parsed query parameters and return the response
        result, metadata = get_user_by_params(params)
        response.set_metadata_direct(metadata)
        response.set_response(result, HTTPStatus.OK)

    except (Exception, ApplicationException) as err:
        logger.error(err)

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    return response.get_response()


# get user by token
@user_bp.route("/users/<user_id>", methods=["GET"])
@token_required
def get_user(current_user: User, user_id: str):
    response = BaseResponse()

    try:
        if str(current_user._id) == user_id:
            # Convert the current user data to a UserResponse object
            current_user = from_dict(
                data_class=UserResponse, data=current_user.as_dict()
            )

            # Set the response data to the current user and return the response
            response.set_response(current_user, HTTPStatus.OK)
        else:
            raise ApplicationException("Unauthorized", HTTPStatus.UNAUTHORIZED)

    except (Exception, ApplicationException) as err:
        logger.error(err)

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    return response.get_response()


# signup user
@user_bp.route("/users/signup", methods=["POST"])
def signup():
    response = BaseResponse()

    try:
        # Parse the request data based on its MIME type
        if request.mimetype == "application/json":
            user_data = from_dict(data_class=CreateUserRequest, data=request.get_json())
        else:
            user_data = from_dict(data_class=CreateUserRequest, data=request.form)

        signup_success = signup_user(user_data)
        if signup_success:
            response.set_response("User registered successfully", HTTPStatus.CREATED)
        else:
            raise ApplicationException("User already exists", HTTPStatus.BAD_REQUEST)

    except (Exception, ApplicationException) as err:
        logger.error(err)

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    return response.get_response()


# login user
@user_bp.route("/users/login", methods=["POST"])
def login():
    response = BaseResponse()
    try:
        # Parse the request data based on its MIME type
        if request.mimetype == "application/json":
            user_data = from_dict(data_class=LoginUserRequest, data=request.get_json())
        else:
            user_data = from_dict(data_class=LoginUserRequest, data=request.form)

        response.set_response(login_user(user_data), HTTPStatus.OK)

    except (Exception, ApplicationException) as err:
        logger.error(err)

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    return response.get_response()


# update user
@user_bp.route("/users", methods=["PUT"])
@token_required
def update_user_data(current_user: User):
    response = BaseResponse()

    try:
        if request.mimetype == "application/json":
            user_data = UpdateUserRequest(
                user_id=current_user._id
                if request.get_json().get("user_id") is None
                else request.get_json().get("user_id"),
                name=request.get_json().get("name"),
                email=request.get_json().get("email"),
                old_password=request.get_json().get("old_password"),
                password=request.get_json().get("password"),
                confirm_password=request.get_json().get("confirm_password"),
            )
        else:
            user_data = UpdateUserRequest(
                user_id=request.form.get("user_id", current_user._id),
                name=request.form.get("name"),
                email=request.form.get("email"),
                old_password=request.form.get("old_password"),
                password=request.form.get("password"),
                confirm_password=request.form.get("confirm_password"),
            )

        logger.error(user_data)
        update_success = update_user(user_data)

        if update_success:
            response.set_response("User updated successfully", HTTPStatus.OK)
        else:
            raise ApplicationException("User not found", HTTPStatus.NOT_FOUND)

    except (Exception, ApplicationException) as err:
        logger.error(err)

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    return response.get_response()


# delete user
@user_bp.route("/users/<user_id>", methods=["DELETE"])
@token_required
@is_admin
def delete_user(current_user: User, user_id: str):
    response = BaseResponse()

    try:
        if str(current_user._id) == user_id:
            response.set_response("Cannot delete current user", HTTPStatus.BAD_REQUEST)
            return response.get_response()

        user_data = UpdateUserRequest(user_id, is_active=False)

        update_success = update_user(user_data)
        if update_success:
            response.set_response("User updated successfully", HTTPStatus.OK)
        else:
            raise ApplicationException("User not found", HTTPStatus.NOT_FOUND)

    except (Exception, ApplicationException) as err:
        logger.error(err)
        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    return response.get_response()


# update user's role
@user_bp.route("/users/role", methods=["PUT"])
@token_required
@is_admin
def update_user_role(current_user: User):
    response = BaseResponse()

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

        update_success = update_user(user_data)
        if update_success:
            response.set_response("User updated successfully", HTTPStatus.OK)
        else:
            raise ApplicationException("User not found", HTTPStatus.NOT_FOUND)

    except (Exception, ApplicationException) as err:
        logger.error(err)

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    return response.get_response()
