import logging
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta
from http import HTTPStatus

import jwt
from config import SECRET_KEY, database
from controllers.utils import token_required
from dacite import from_dict
from flask import request
from request.user.UserRequest import CreateUserRequest, LoginUserRequest
from response.BaseResponse import BaseResponse
from response.PaginateResponse import PaginateResponse
from response.user.UserResponse import UserResponse
from utils.CustomFormatter import init_logging
from werkzeug.security import check_password_hash, generate_password_hash

init_logging()
logger = logging.getLogger(__name__)

# ======== GET : get all users ========
@token_required
def get_all_users(current_user):
    response = PaginateResponse()
    users = database["users"]
    output = []

    page = int(__get_params(0, "page"))
    limit = int(__get_params(10, "limit"))
    sorts = __get_params("_id,ASC", "sort")
    sort_field = sorts.split(',')[0]
    sort_order = sorts.split(',')[1]

    count = users.count_documents({})
    for user in users.find().sort(sort_field, 1 if sort_order == "ASC" else -1).skip(limit * page).limit(limit):
        res = from_dict(data_class=UserResponse, data=user)
        output.append(res.__dict__)

    response.set_metadata(page, limit, count)
    response.set_response(output, HTTPStatus.OK)
    return response.__dict__, response.status

# ======== GET : get user by token ========
@token_required 
def get_user(current_user):
    response = BaseResponse()
    current_user = from_dict(data_class=UserResponse, data=current_user)
    if current_user:
        response.set_response(current_user, HTTPStatus.OK)
    else:
        response.set_response("User not found", HTTPStatus.NOT_FOUND)
    return response.__dict__, response.status

# ======== POST : create user ========
def signup_user():
    response = BaseResponse()
    users = database["users"]

    if request.mimetype == "application/json":
        user_data = from_dict(data_class=CreateUserRequest, data=request.get_json())
    else:
        user_data = from_dict(data_class=CreateUserRequest, data=request.form)

    user_res = users.find_one({"email" : user_data.email})
    if user_res:
        response.set_response("User already exists", HTTPStatus.BAD_REQUEST)
    else:
        hashed_password = generate_password_hash(user_data.password, "sha256", 24)
        user_data.password = hashed_password
        user_data.user_id = str(uuid.uuid4())
        users.insert_one(asdict(user_data))
        response.set_response("User created successfully", HTTPStatus.CREATED)
        
    return response.__dict__, response.status

# ======== POST : login user ========
def login_user():
    response = BaseResponse()
    try:
        users = database["users"]
        if request.mimetype == "application/json":
            login_request = from_dict(data_class=LoginUserRequest, data=request.get_json())
        else:
            login_request = from_dict(data_class=LoginUserRequest, data=request.form)
        user_res = users.find_one({"email" : login_request.email})

        if user_res:
            if check_password_hash(user_res["password"], login_request.password):
                user_res = from_dict(data_class=UserResponse, data=user_res)
                user_encode = asdict(user_res)
                user_encode["exp"] = datetime.utcnow() + timedelta(hours=24)
                access_token = jwt.encode(user_encode, SECRET_KEY, algorithm="HS256")
                response.set_response({"token": access_token, "user_data": user_res}, HTTPStatus.OK)
            else:
                response.set_response("Invalid username and password", HTTPStatus.BAD_REQUEST)
        else:
            response.set_response("No results found", HTTPStatus.NOT_FOUND)
        return response.__dict__, response.status
    except Exception as e:
        logger.error(e)
        response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)
        return response.__dict__, response.status

def __get_params(default_value, field):
    return default_value if request.args.get(field) == None else request.args.get(field)
