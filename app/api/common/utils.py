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
    Decorator to check if the user is logged in
    """
    @wraps(func)
    def decorated(*args, **kwargs):
        response = BaseResponse()
        token = None
        # jwt is passed in the request header
        if "Authorization" in request.headers:
            token = request.headers["Authorization"]
            token = token.split("Bearer")[1].strip()
        # return 401 if token is not passed
        if not token:
            response.set_response("Token is missing", 401)
            return response.get_response()

        try:
            # decoding the payload to fetch the stored details
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = database["users"].find_one({"email": data["email"]})
            if not current_user:
                raise ApplicationException(
                    "User not found", HTTPStatus.UNAUTHORIZED)
        except jwt.ExpiredSignatureError as err:
            logger.error(str(err))
            response.set_response("Token is expired", 401)
            return response.get_response()
        except ApplicationException as err:
            logger.error(str(err))
            response.set_response(str(err), err.status)
            return response.get_response()
        # returns the current logged in users contex to the routes
        return func(current_user, *args, **kwargs)

    return decorated


def clean_query_params(query_params: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Clean query params
    :param `query_params`: query params
    :return: `query` and `pagination`
    """
    query = {}
    pagination = {}

    for key, value in query_params.items():
        if key == 'page' or key == 'limit':
            pagination[key] = int(value)
        else:
            query[key] = value

    return query, pagination


def parse_query_params(query_params: Dict[str, str]) -> Tuple[Dict[str, any], Dict[str, int]]:
    """
    Parse query params to criteria and sorting
    :param `query_params`: query params
    :return: `criteria` and `sorting`
    """
    supported_operators = {
        'in': handle_in_operator,
        'nin': handle_nin_operator,
        'gt': handle_gt_operator,
        'gte': handle_gte_operator,
        'lt': handle_lt_operator,
        'lte': handle_lte_operator,
        'exists': handle_exists_operator
    }
    criteria = {}
    sorting = {}

    for key, value in query_params.items():
        # Split key into field and operator
        key_parts = key.split('.')
        if len(key_parts) == 1:
            field, operator = key, None
        else:
            field_parts, operator = key_parts[:-1], key_parts[-1]
            field = '.'.join(field_parts)

        # Handle operator
        if operator and operator not in supported_operators:
            raise ApplicationException(
                f'Unsupported operator: {operator}', HTTPStatus.BAD_REQUEST)

        # Handle field
        if operator in supported_operators:
            supported_operators[operator](criteria, field, value)
        elif key == 'sort':
            field, order = value.split(',')
            sorting["field"] = field
            sorting["direction"] = ASCENDING if order == 'ASC' else DESCENDING
        else:
            handle_default_operator(criteria, field, value)

    return criteria, sorting


def handle_in_operator(criteria: Dict[str, any], field: str, value: str):
    criteria[field] = {'$in': value.split(',')}


def handle_nin_operator(criteria: Dict[str, any], field: str, value: str):
    criteria[field] = {'$nin': value.split(',')}


def handle_gt_operator(criteria: Dict[str, any], field: str, value: str):
    try:
        value = datetime.strptime(
            value, '%Y-%m-%d').astimezone(timezone("Asia/Jakarta"))
    except ValueError:
        pass
    criteria[field] = {'$gt': value}


def handle_gte_operator(criteria: Dict[str, any], field: str, value: str):
    try:
        value = datetime.strptime(
            value, '%Y-%m-%d').astimezone(timezone("Asia/Jakarta"))
    except ValueError:
        pass
    criteria[field] = {'$gte': value}


def handle_lt_operator(criteria: Dict[str, any], field: str, value: str):
    try:
        value = datetime.strptime(
            value, '%Y-%m-%d').astimezone(timezone("Asia/Jakarta"))
    except ValueError:
        pass
    criteria[field] = {'$lt': value}


def handle_lte_operator(criteria: Dict[str, any], field: str, value: str):
    try:
        value = datetime.strptime(
            value, '%Y-%m-%d').astimezone(timezone("Asia/Jakarta"))
    except ValueError:
        pass
    criteria[field] = {'$lte': value}


def handle_exists_operator(criteria: Dict[str, any], field: str, value: str):
    criteria[field] = {'$exists': value.lower() == 'true'}


def handle_default_operator(criteria: Dict[str, any], field: str, value: str):
    if field == 'id':
        field = '_id'
        value = ObjectId(value)
    criteria[field] = value
