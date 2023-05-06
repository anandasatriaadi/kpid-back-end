import logging
import math
import re
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Dict, List, Union

import jwt
from bson import ObjectId
from dacite import from_dict
from pytz import timezone
from werkzeug.security import check_password_hash, generate_password_hash

from app.api.common.utils import clean_query_params, parse_query_params
from app.dto import (BaseResponse, CreateUserRequest, PaginateResponse, User,
                     UserResponse)
from config import DATABASE, SECRET_KEY

logger = logging.getLogger(__name__)
USER_DB = DATABASE["users"]

# ======== Get users by params ========
def get_user_by_params(query_params: Dict[str, str]) -> List[Dict[str, str]]:
    """
    A function that fetches users from the database based on the query parameters provided.

    Args:
    query_params (Dict[str, str]): A dictionary of query parameters.

    Returns:
    List[Dict[str, str]]: A list containing dictionaries of users' details.
    """

    response = PaginateResponse()

    try:
        output = []
        total_elements = USER_DB.count_documents({})

        # Separating the query parameters into query and pagination parameters
        params, pagination = clean_query_params(query_params)

        # Parsing the query parameters to get the fields to be queried and the sort parameters
        query, sort = parse_query_params(params)

        # Fetching users based on the query parameters, sorting them, and paginating the results
        for user in USER_DB.find(query).sort(sort["field"], sort["direction"]).skip(pagination["limit"] * pagination["page"]).limit(pagination["limit"]):
            # Converting the user data to a UserResponse object and adding it to the output list
            res = from_dict(data_class=UserResponse, data=user)
            output.append(res.__dict__)

        # Setting the metadata for the response
        response.set_metadata(pagination["page"], pagination["limit"], total_elements, math.ceil(
            total_elements/pagination["limit"]))
        response.set_response(output, HTTPStatus.OK)

    except Exception as err:
        logger.error(err)
        # Setting the response for internal server error
        response.set_response("Internal server error",
                              HTTPStatus.INTERNAL_SERVER_ERROR)

    # Returning the response as a list of user dictionaries
    return response.get_response()


# ======== POST : create user ========
def signup_user(create_request: CreateUserRequest) -> Dict[str, Union[str, int]]:
    """
    A function that creates a new user in the database with the details provided in the CreateUserRequest object.

    Args:
    create_request (CreateUserRequest): An object containing the details of the user to be created.

    Returns:
    Dict[str, Union[str, int]]: A dictionary containing the response message and HTTP status code.
    """

    response = BaseResponse()
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    try:
        # Checking if the email address provided is valid
        if not re.match(email_pattern, create_request.email):
            response.set_response("Invalid email address", HTTPStatus.BAD_REQUEST)
        else:
            # Checking if the user already exists in the database
            user_res = USER_DB.find_one({"email": create_request.email.lower()})
            if user_res:
                response.set_response("User already exists", HTTPStatus.BAD_REQUEST)
            else:
                # Generating a hashed password and setting the user_id for the new user
                hashed_password = generate_password_hash(
                    create_request.password, "sha256", 24)
                create_request.password = hashed_password
                create_request.user_id = str(uuid.uuid4())

                # Inserting the new user details into the database
                USER_DB.insert_one(asdict(create_request))

                # Setting the response for successful user creation
                response.set_response("User created successfully", HTTPStatus.CREATED)

    except Exception as err:
        logger.error(err)
        # Setting the response for internal server error
        response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)

    # Returning the response as a dictionary
    return response.get_response()


# ======== POST : login user ========
def login_user(create_request: CreateUserRequest) -> Dict[str, Union[Dict[str, Union[str, datetime]], str, int]]:
    """
    A function that logs in a user with the email address and password provided in the CreateUserRequest object.

    Args:
    create_request (CreateUserRequest): An object containing the email address and password of the user to be logged in.

    Returns:
    Dict[str, Union[Dict[str, Union[str, datetime]], str, int]]: A dictionary containing the access token and user data, if login is successful, or an error message and HTTP status code, if not.
    """

    response = BaseResponse()
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    try:
        # Checking if the email address provided is valid
        if not re.match(email_pattern, create_request.email):
            response.set_response("Invalid email address", HTTPStatus.BAD_REQUEST)
        else:
            # Checking if a user with the provided email address exists in the database
            user_res = User.from_document(USER_DB.find_one({"email": create_request.email}))
            if user_res:
                # Checking if the password provided is correct
                if check_password_hash(user_res.password, create_request.password):
                    # Updating the last login time of the user
                    user_res.last_login = datetime.now(timezone("Asia/Jakarta"))
                    USER_DB.update_one({"_id": ObjectId(user_res._id)}, {"$set": asdict(user_res)})
                    # Converting the user data to a UserResponse object and encoding it as a JWT access token
                    user_res = from_dict(data_class=UserResponse, data=asdict(user_res))
                    user_encode = asdict(user_res)
                    user_encode["exp"] = datetime.utcnow() + timedelta(hours=12)
                    access_token = jwt.encode(
                        user_encode, SECRET_KEY, algorithm="HS256")

                    # Setting the response with the access token and user data
                    response.set_response(
                        {"token": access_token, "user_data": user_res}, HTTPStatus.OK)
                else:
                    # Setting the response for incorrect password
                    response.set_response(
                        "Invalid email and password", HTTPStatus.BAD_REQUEST)
            else:
                # Setting the response for no user found with the provided email address
                response.set_response("No email found", HTTPStatus.NOT_FOUND)
    except Exception as err:
        logger.error(err)
        # Setting the response for internal server error
        response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)

    # Returning the response as a dictionary
    return response.get_response()



