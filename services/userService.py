from http import HTTPStatus
import logging
from flask import request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from controllers.utils import token_required
import jwt
from datetime import datetime, timedelta

from config import database, SECRET_KEY
from response.BaseResponse import BaseResponse
from response.user.UserResponse import UserResponse
from utils.CustomFormatter import init_logging

init_logging()
logger = logging.getLogger(__name__)

# ======== GET : get all users ========
@token_required
def get_all_users(current_user):
    response = BaseResponse()
    users = database["users"]
    output = []

    for user in users.find():
        res = UserResponse(user.get('name'), user.get('email'), user.get('profile'))
        output.append(res.__dict__)

    response.setResponse(output, HTTPStatus.OK)
    return response.__dict__, response.status

# ======== POST : create user ========
def signup_user():
    response = BaseResponse()
    users = database["users"]

    name = request.form.get('name')
    email = request.form.get('email')

    user_res = users.find_one({'email' : email})
    if user_res:
        response.setResponse("User already exists", HTTPStatus.BAD_REQUEST)
    else:
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, 'sha256', 24)
        users.insert_one({'name': name, 'email': email, 'password': hashed_password})
        response.setResponse("User created successfully", HTTPStatus.CREATED)
        
    return response.__dict__, response.status

# ======== POST : login user ========
def login_user():
    response = BaseResponse()
    try:
        users = database["users"]
        email = request.form.get('email')
        password = request.form.get('password')
        user_res = users.find_one({'email' : email})
        if user_res:
            if check_password_hash(user_res['password'], password):
                access_token = jwt.encode({
                    'name': user_res['name'],
                    'email': user_res['email'],
                    'exp' : datetime.utcnow() + timedelta(minutes = 30)
                }, SECRET_KEY, algorithm="HS256")
                response.setResponse({"token": access_token}, HTTPStatus.OK)
            else:
                response.setResponse("Invalid username and password", HTTPStatus.BAD_REQUEST)
        else:
            response.setResponse("No results found", HTTPStatus.NOT_FOUND)
        return response.__dict__, response.status
    except Exception as e:
        logger.error(e)
        response.setResponse("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)
        return response.__dict__, response.status