import logging
import math
import uuid
import re
from dataclasses import asdict
from datetime import datetime, timedelta
from http import HTTPStatus

import jwt
from dacite import from_dict
from werkzeug.security import check_password_hash, generate_password_hash

from app.dto import (BaseResponse, CreateUserRequest, PaginateResponse, UserResponse)
from app.api.common.utils import clean_query_params, parse_query_params
from config import SECRET_KEY, database

logger = logging.getLogger(__name__)


# ======== Get users by params ========
def get_user_by_params(query_params: dict) -> PaginateResponse:
    response = PaginateResponse()
    users = database["users"]

    try:
        output = []
        total_elements = users.count_documents({})

        params, pagination = clean_query_params(query_params)
        query, sort = parse_query_params(params)

        for user in users.find(query).sort(params["sort_field"], 1 if params["sort_order"] == "ASC" else -1).skip(params["limit"] * params["page"]).limit(params["limit"]):
            res = from_dict(data_class=UserResponse, data=user)
            output.append(res.__dict__)

        response.set_metadata(params["page"], params["limit"], total_elements, math.ceil(
            total_elements/params["limit"]))
        response.set_response(output, HTTPStatus.OK)
    except Exception as err:
        logger.error(err)
        response.set_response("Internal server error",
                              HTTPStatus.INTERNAL_SERVER_ERROR)
    return response.get_response()


# ======== POST : create user ========
def signup_user(create_request: CreateUserRequest) -> BaseResponse:
    response = BaseResponse()
    users = database["users"]
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    try:
        if not re.match(email_pattern, create_request.email):
            response.set_response("Invalid email address", HTTPStatus.BAD_REQUEST)
        else:
            user_res = users.find_one({"email": create_request.email.lower()})
            if user_res:
                response.set_response("User already exists", HTTPStatus.BAD_REQUEST)
            else:
                hashed_password = generate_password_hash(
                    create_request.password, "sha256", 24)
                create_request.password = hashed_password
                create_request.user_id = str(uuid.uuid4())
                users.insert_one(asdict(create_request))
                response.set_response("User created successfully", HTTPStatus.CREATED)
    except Exception as err:
        logger.error(err)
        response.set_response("Internal server error",
                              HTTPStatus.INTERNAL_SERVER_ERROR)
    return response.get_response()


# ======== POST : login user ========
def login_user(create_request: CreateUserRequest) -> BaseResponse:
    response = BaseResponse()
    users = database["users"]
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    try:
        if not re.match(email_pattern, create_request.email):
            response.set_response("Invalid email address", HTTPStatus.BAD_REQUEST)
        else:
            user_res = users.find_one({"email": create_request.email})
            if user_res:
                if check_password_hash(user_res["password"], create_request.password):
                    user_res = from_dict(data_class=UserResponse, data=user_res)
                    user_encode = asdict(user_res)
                    user_encode["exp"] = datetime.utcnow() + timedelta(hours=24)
                    access_token = jwt.encode(
                        user_encode, SECRET_KEY, algorithm="HS256")
                    response.set_response(
                        {"token": access_token, "user_data": user_res}, HTTPStatus.OK)
                else:
                    response.set_response(
                        "Invalid username and password", HTTPStatus.BAD_REQUEST)
            else:
                response.set_response("No results found", HTTPStatus.NOT_FOUND)
    except Exception as err:
        logger.error(err)
        response.set_response("Internal server error",
                              HTTPStatus.INTERNAL_SERVER_ERROR)
    return response.get_response()
