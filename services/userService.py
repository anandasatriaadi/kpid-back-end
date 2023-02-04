import logging
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
from response.user.UserResponse import UserResponse
from utils.CustomFormatter import init_logging
from werkzeug.security import check_password_hash, generate_password_hash

init_logging()
logger = logging.getLogger(__name__)

# ======== GET : get all users ========
@token_required
def get_all_users(current_user):
    response = BaseResponse()
    users = database["users"]
    output = []

    for user in users.find():
        res = from_dict(data_class=UserResponse, data=user)
        output.append(res.__dict__)

    response.setResponse(output, HTTPStatus.OK)
    return response.__dict__, response.status

# ======== GET : get user by token ========
@token_required
def get_user(current_user):
    response = BaseResponse()
    current_user = from_dict(data_class=UserResponse, data=current_user)
    response.setResponse(current_user, HTTPStatus.OK)
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
        response.setResponse("User already exists", HTTPStatus.BAD_REQUEST)
    else:
        hashed_password = generate_password_hash(user_data.password, "sha256", 24)
        user_data.password = hashed_password
        users.insert_one(asdict(user_data))
        response.setResponse("User created successfully", HTTPStatus.CREATED)
        
    return response.__dict__, response.status

# ======== POST : login user ========
def login_user():
    response = BaseResponse()
    try:
        users = database["users"]
        if request.mimetype == "application/json":
            json_data = request.get_json()
            userRequest = from_dict(data_class=LoginUserRequest, data=json_data)
        else:
            userRequest = from_dict(data_class=LoginUserRequest, data=request.form)
        logger.info(userRequest)
        user_res = users.find_one({"email" : userRequest.email})

        if user_res:
            if check_password_hash(user_res["password"], userRequest.password):
                access_token = jwt.encode({
                    "name": user_res["name"],
                    "email": user_res["email"],
                    "exp" : datetime.utcnow() + timedelta(hours = 24)
                }, SECRET_KEY, algorithm="HS256")
                user_res = from_dict(data_class=UserResponse, data=user_res)
                response.setResponse({"token": access_token, "user_data": user_res}, HTTPStatus.OK)
            else:
                response.setResponse("Invalid username and password", HTTPStatus.BAD_REQUEST)
        else:
            response.setResponse("No results found", HTTPStatus.NOT_FOUND)
        return response.__dict__, response.status
    except Exception as e:
        logger.error(e)
        response.setResponse("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)
        return response.__dict__, response.status