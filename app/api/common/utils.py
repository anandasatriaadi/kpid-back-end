import logging
from datetime import datetime
from functools import wraps
from http import HTTPStatus
from typing import Dict, Tuple

import jwt
from bson.objectid import ObjectId
from flask import request
from pymongo import ASCENDING, DESCENDING
from pytz import timezone

from app.api.exceptions import ApplicationException
from app.dto import BaseResponse
from config import SECRET_KEY, database

logger = logging.getLogger(__name__)


def token_required(func):
    """
    A decorator function that requires a valid JWT token to be present in the request headers.
    If a valid token is present, it decodes the token to fetch the stored user details and passes them to the decorated function.

    Example usage:
    @token_required
    def protected_route(current_user):
        # do something with current_user
        pass
    """

    # Wrapping the decorated function with the "wraps" decorator to preserve its metadata
    @wraps(func)
    def decorated(*args, **kwargs):
        # Initializing a new BaseResponse object
        response = BaseResponse()
        # Initializing the token variable to None
        token = None

        # Checking if the Authorization header is present in the request headers
        if "Authorization" in request.headers:
            # Parsing the token from the Authorization header
            token = request.headers["Authorization"]
            token = token.split("Bearer")[1].strip()

        # If the token is not present, return a 401 Unauthorized response
        if not token:
            response.set_response("Token is missing", 401)
            return response.get_response()

        try:
            # Decoding the token to fetch the stored user details
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            # Querying the database to fetch the current user based on the email stored in the token
            current_user = database["users"].find_one({"email": data["email"]})
            # If the user is not found, raise an ApplicationException with a UNAUTHORIZED status
            if not current_user:
                raise ApplicationException(
                    "User not found", HTTPStatus.UNAUTHORIZED)
        except jwt.ExpiredSignatureError as err:
            logger.error(str(err))
            # If the token is expired, return a 401 Unauthorized response
            response.set_response("Token is expired", 401)
            return response.get_response()
        except ApplicationException as err:
            logger.error(str(err))
            # If an ApplicationException is raised, return an appropriate response based on the error message and status code
            response.set_response(str(err), err.status)
            return response.get_response()

        # If the token is valid and the current user is found, pass the current_user object and any other arguments to the decorated function and return its result
        return func(current_user, *args, **kwargs)

    # Returning the decorated function
    return decorated


def clean_query_params(query_params: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    A function that processes a dictionary of query parameters and separates them into two dictionaries:
    one for pagination parameters and one for query parameters.

    Args:
    query_params (Dict[str, str]): A dictionary of query parameters.

    Returns:
    Tuple[Dict[str, str], Dict[str, str]]: A tuple containing two dictionaries: one for query parameters and one for pagination parameters.

    Example usage:
    query, pagination = clean_query_params(query_params)
    """

    # Initializing empty dictionaries for query parameters and pagination parameters
    query = {}
    pagination = {}

    # Iterating over each key-value pair in the query_params dictionary
    for key, value in query_params.items():
        # If the key is "page" or "limit", convert the value to an integer and add it to the pagination dictionary
        if key == 'page' or key == 'limit':
            pagination[key] = int(value)
        # Otherwise, add the key-value pair to the query dictionary
        else:
            query[key] = value

    # Returning a tuple containing the query dictionary and the pagination dictionary
    return query, pagination


def parse_query_params(query_params: Dict[str, str]) -> Tuple[Dict[str, any], Dict[str, int]]:
    """
    A function that parses the query parameters and separates them into criteria for querying the database and sorting parameters.

    Args:
    query_params (Dict[str, str]): A dictionary of query parameters.

    Returns:
    Tuple[Dict[str, Any], Dict[str, int]]: A tuple containing a dictionary of query criteria and a dictionary of sorting parameters.

    Example usage:
    criteria, sorting = parse_query_params(query_params)
    """

    supported_operators = {
        'in': __handle_in_operator,
        'nin': __handle_nin_operator,
        'gt': __handle_gt_operator,
        'gte': __handle_gte_operator,
        'lt': __handle_lt_operator,
        'lte': __handle_lte_operator,
        'exists': __handle_exists_operator
    }

    criteria = {}
    sorting = {}

    # Iterating over each key-value pair in the query_params dictionary
    for key, value in query_params.items():
        key_parts = key.split('.')
        if len(key_parts) == 1:
            field, operator = key, None
        else:
            field_parts, operator = key_parts[:-1], key_parts[-1]
            field = '.'.join(field_parts)

        # Checking if the operator is supported, and calling the corresponding function
        if operator and operator not in supported_operators:
            raise ApplicationException(
                f'Unsupported operator: {operator}', HTTPStatus.BAD_REQUEST)

        if operator in supported_operators:
            supported_operators[operator](criteria, field, value)
        # If the key is "sort", setting the sorting parameters
        elif key == 'sort':
            field, order = value.split(',')
            sorting["field"] = field
            sorting["direction"] = ASCENDING if order == 'ASC' else DESCENDING
        # If the key is not "sort", using the default equality operator
        else:
            __handle_default_operator(criteria, field, value)

    # Returning a tuple containing the criteria dictionary and the sorting dictionary
    return criteria, sorting


def __handle_in_operator(criteria: Dict[str, any], field: str, value: str):
    criteria[field] = {'$in': value.split(',')}


def __handle_nin_operator(criteria: Dict[str, any], field: str, value: str):
    criteria[field] = {'$nin': value.split(',')}


def __handle_gt_operator(criteria: Dict[str, any], field: str, value: str):
    try:
        value = datetime.strptime(
            value, '%Y-%m-%d').astimezone(timezone("Asia/Jakarta"))
    except ValueError:
        pass
    criteria[field] = {'$gt': value}


def __handle_gte_operator(criteria: Dict[str, any], field: str, value: str):
    try:
        value = datetime.strptime(
            value, '%Y-%m-%d').astimezone(timezone("Asia/Jakarta"))
    except ValueError:
        pass
    criteria[field] = {'$gte': value}


def __handle_lt_operator(criteria: Dict[str, any], field: str, value: str):
    try:
        value = datetime.strptime(
            value, '%Y-%m-%d').astimezone(timezone("Asia/Jakarta"))
    except ValueError:
        pass
    criteria[field] = {'$lt': value}


def __handle_lte_operator(criteria: Dict[str, any], field: str, value: str):
    try:
        value = datetime.strptime(
            value, '%Y-%m-%d').astimezone(timezone("Asia/Jakarta"))
    except ValueError:
        pass
    criteria[field] = {'$lte': value}


def __handle_exists_operator(criteria: Dict[str, any], field: str, value: str):
    criteria[field] = {'$exists': value.lower() == 'true'}


def __handle_default_operator(criteria: Dict[str, any], field: str, value: str):
    if field == 'id':
        field = '_id'
        value = ObjectId(value)
    criteria[field] = value
