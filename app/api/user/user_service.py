import logging
import math
import re
from dataclasses import asdict
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Dict, List, Tuple, Union

import jwt
import pytz
from bson import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash

from app.api.common.query_utils import clean_query_params, parse_query_params
from app.api.exceptions import ApplicationException
from app.dto import (
    CreateActivityRequest,
    CreateUserRequest,
    LoginUserRequest,
    Metadata,
    UpdateUserRequest,
    User,
    UserResponse,
)
from config import DATABASE, SECRET_KEY

logger = logging.getLogger(__name__)
USER_DB = DATABASE["users"]
ACTIVITY_DB = DATABASE["activity"]


# Get users by params
def get_user_by_params(
    query_params: Dict[str, str]
) -> Tuple[List[UserResponse], Metadata]:
    """
    A function that fetches users from the database based on the query parameters provided.

    Args:
    query_params (Dict[str, str]): A dictionary of query parameters.

    Returns:
    Tuple[List[UserResponse], Metadata]: A list containing dictionaries of users' details.
    """

    output = []

    # Separating the query parameters into query and pagination parameters
    params, pagination = clean_query_params(query_params)
    query, sort = parse_query_params(params)

    total_elements = USER_DB.count_documents(query)
    # Fetching users based on the query parameters, sorting them, and paginating the results
    results = USER_DB.find(query)
    if len(sort) > 0:
        results = results.sort(sort["field"], sort["direction"])
    if len(pagination) > 0:
        results = results.skip(pagination["limit"] * pagination["page"]).limit(
            pagination["limit"]
        )

    for user in results:
        res = UserResponse.from_document(User.from_document(user).as_dict())
        output.append(res)

    # Setting the metadata for the response
    metadata = Metadata(
        pagination["page"],
        pagination["limit"],
        total_elements,
        math.ceil(total_elements / pagination["limit"]),
    )
    return output, metadata


# POST : create user
def signup_user(create_request: CreateUserRequest) -> bool:
    """
    A function that creates a new user in the database with the details provided in the CreateUserRequest object.

    Args:
    create_request (CreateUserRequest): An object containing the details of the user to be created.

    Returns:
    bool: A dictionary containing the response message and HTTP status code.
    """
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    password_pattern = r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$"

    # Checking if the email address provided is valid
    if not re.match(email_pattern, create_request.email):
        raise ApplicationException("Alamat Email Tidak Valid", HTTPStatus.BAD_REQUEST)
    # Checking if the password meets the requirements
    elif not re.match(password_pattern, create_request.password):
        raise ApplicationException(
            "Password must be at least 8 characters long and contain both letters and numbers.",
            HTTPStatus.BAD_REQUEST,
        )
    # Checking if the passwords match
    elif create_request.password != create_request.confirm_password:
        raise ApplicationException("Password Tidak Cocok", HTTPStatus.BAD_REQUEST)
    else:
        # Checking if the user already exists in the database
        user_res = USER_DB.find_one({"email": create_request.email.lower()})
        if user_res:
            raise ApplicationException(
                "Pengguna Sudah Ada di Sistem", HTTPStatus.BAD_REQUEST
            )
        else:
            # Generating a hashed password for the new user
            hashed_password = generate_password_hash(
                create_request.password, "sha256", 24
            )
            create_request.password = hashed_password

            create_request_dict = asdict(create_request)
            create_request_dict.pop("confirm_password")
            # Inserting the new user details into the database
            inserted_id = USER_DB.insert_one(create_request_dict).inserted_id

            try:
                # Setting the response for successful user creation
                inserted_user = User.from_document(
                    USER_DB.find_one({"_id": inserted_id})
                )
                inserted_user = UserResponse.from_document(inserted_user.as_dict())
                user_encode = inserted_user.as_dict()
                user_encode["exp"] = datetime.utcnow() + timedelta(hours=12)
                access_token = jwt.encode(user_encode, SECRET_KEY, algorithm="HS256")

                # Setting the response with the access token and user data
                result = {"token": access_token, "user_data": inserted_user}
                return result
            except Exception as err:
                logger.error(str(err))
                USER_DB.delete_one({"_id": inserted_id})
                raise ApplicationException(
                    "Terjadi Kesalahan Saat Membuat Pengguna",
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )


# POST : login user
def login_user(
    login_request: LoginUserRequest,
) -> Dict[str, any]:
    """
    A function that logs in a user with the email address and password provided in the LoginUserRequest object.

    Args:
    create_request (LoginUserRequest): An object containing the email address and password of the user to be logged in.

    Returns:
    Dict[str, Union[Dict[str, Union[str, datetime]], str, int]]: A dictionary containing the access token and user data, if login is successful, or an error message and HTTP status code, if not.
    """

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    # Checking if the email address provided is valid
    if not re.match(email_pattern, login_request.email):
        raise ApplicationException("Invalid email address", HTTPStatus.BAD_REQUEST)
    else:
        # Checking if a user with the provided email address exists in the database
        user_res = USER_DB.find_one({"email": login_request.email.casefold()})
        if user_res is not None:
            user_res = User.from_document(user_res)
            # Checking if the password provided is correct
            if not user_res.is_active:
                raise ApplicationException(
                    "Tidak dapat Login. Pengguna Sudah Non Aktif",
                    HTTPStatus.BAD_REQUEST,
                )
            elif check_password_hash(user_res.password, login_request.password):
                # Updating the last login time of the user
                user_res.last_login = datetime.utcnow()
                USER_DB.update_one(
                    {"_id": ObjectId(user_res._id)}, {"$set": asdict(user_res)}
                )

                # Converting the user data to a UserResponse object and encoding it as a JWT access token
                user_res = UserResponse.from_document(user_res.as_dict())
                user_encode = user_res.as_dict()
                user_encode["exp"] = datetime.utcnow() + timedelta(hours=12)
                access_token = jwt.encode(user_encode, SECRET_KEY, algorithm="HS256")

                # Setting the response with the access token and user data
                result = {"token": access_token, "user_data": user_res}
                return result
            else:
                # Setting the response for incorrect password
                raise ApplicationException(
                    "Email atau Password Tidak Valid", HTTPStatus.BAD_REQUEST
                )
        else:
            raise ApplicationException(
                "Email atau Password Tidak Valid", HTTPStatus.BAD_REQUEST
            )


# Update user
def update_user(update_user_request: UpdateUserRequest) -> bool:
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    password_pattern = r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$"

    user_res = USER_DB.find_one({"_id": ObjectId(update_user_request.user_id)})
    if user_res is not None:
        update_data = {}

        # Checking through all properties to make sure that no data is change to None or null on update
        if update_user_request.name is not None:
            update_data["name"] = update_user_request.name

        if (
            update_user_request.email is not None
            and user_res["email"] != update_user_request.email
        ):
            logger.debug(f"{user_res['email']} {update_user_request.email}")
            if re.match(email_pattern, update_user_request.email):
                if USER_DB.find_one({"email": update_user_request.email.lower()}):
                    raise ApplicationException(
                        "Email Sudah Terdaftar di Sistem", HTTPStatus.BAD_REQUEST
                    )
                update_data["email"] = update_user_request.email.lower()
            else:
                raise ApplicationException(
                    "Alamat Email Tidak Valid", HTTPStatus.BAD_REQUEST
                )

        if update_user_request.role is not None:
            update_data["role"] = update_user_request.role

        if update_user_request.is_active is not None:
            update_data["is_active"] = update_user_request.is_active

        if update_user_request.old_password is not None:
            if check_password_hash(
                user_res["password"], update_user_request.old_password
            ):
                if update_user_request.password != update_user_request.confirm_password:
                    raise ApplicationException(
                        "Password Baru Tidak Cocok!", HTTPStatus.BAD_REQUEST
                    )
                elif not re.match(password_pattern, update_user_request.password):
                    raise ApplicationException(
                        "Kata Sandi Harus Terdiri dari Minimal 8 Karakter dan Mengandung Kombinasi Huruf dan Angka",
                        HTTPStatus.BAD_REQUEST,
                    )
                else:
                    hashed_password = generate_password_hash(
                        update_user_request.password, "sha256", 24
                    )
                    update_data["password"] = hashed_password
            else:
                raise ApplicationException(
                    "Password Lama Tidak Sesuai!", HTTPStatus.BAD_REQUEST
                )

        USER_DB.update_one(
            {"_id": ObjectId(update_user_request.user_id)}, {"$set": update_data}
        )
        return True
    else:
        raise ApplicationException("Pengguna Tidak Ditemukan", HTTPStatus.NOT_FOUND)


# aggregate user login
def aggregate_user_login() -> bool:
    try:
        today = datetime.now()
        start_date = today.replace(hour=0, minute=0, second=0).astimezone(
            pytz.timezone("Asia/Jakarta")
        )
        end_date = today.replace(hour=23, minute=59, second=59).astimezone(
            pytz.timezone("Asia/Jakarta")
        )

        # Create the aggregation pipeline
        pipeline = [
            {
                "$match": {
                    "last_login": {"$gte": start_date, "$lte": end_date},
                    "is_active": True,
                },
            },
            {
                "$project": {
                    "_id": 0,
                    "name": 1,
                    "email": 1,
                    "last_login": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": {
                                "$dateAdd": {
                                    "startDate": "$last_login",
                                    "unit": "hour",
                                    "amount": 8,
                                }
                            },
                        }
                    },
                }
            },
            {
                "$group": {
                    "_id": "$last_login",
                    "count": {"$sum": 1},
                    "users": {"$push": {"name": "$name", "email": "$email"}},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        # Execute the aggregation query
        result = USER_DB.aggregate(pipeline)

        documents = list(result)

        # Insert the result into ACTIVITY_DB
        for doc in documents:
            # Convert _id to datetime and set the time to 23:59:59
            date_string = doc["_id"]
            date = datetime.strptime(date_string, "%Y-%m-%d")
            end_of_day = date.replace(hour=23, minute=59, second=59).astimezone(
                pytz.timezone("Asia/Jakarta")
            )

            # Set the modified _id and insert the document
            data = CreateActivityRequest(
                date=end_of_day, users_count=doc["count"], users=doc["users"]
            )
            ACTIVITY_DB.insert_one(asdict(data))

        return True
    except Exception as err:
        logger.error(str(err))
        return False
