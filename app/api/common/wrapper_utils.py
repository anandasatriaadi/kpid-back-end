import logging
from functools import wraps
from http import HTTPStatus
from typing import Callable

import jwt
from flask import request

from app.api.exceptions import ApplicationException
from app.dto import BaseResponse
from config import DATABASE, SECRET_KEY

logger = logging.getLogger(__name__)


def token_required(func: Callable) -> Callable:
    """
    A decorator function that requires a valid JWT token to be present in the request headers.
    If a valid token is present, it decodes the token to fetch the stored user details and passes them to the decorated function.

    Example usage:
    @token_required
    def protected_route(current_user):
        # do something with current_user
        pass
    """

    @wraps(func)
    def decorated(*args, **kwargs):
        response = BaseResponse()

        # Checking if the Authorization header is present in the request headers
        token = request.headers.get("Authorization").split("Bearer")[-1].strip()
        
        # If the token is not present, return a 401 Unauthorized response
        if not token:
            response.set_response("Token is missing", 401)
            return response.get_response()

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = DATABASE["users"].find_one({"email": data["email"]})

            if not current_user:
                raise ApplicationException(
                    "User not found", HTTPStatus.UNAUTHORIZED)

        except (jwt.ExpiredSignatureError, ApplicationException) as err:
            logger.error(str(err))
            status_code = 401 if isinstance(
                err, jwt.ExpiredSignatureError) else err.status
            response.set_response(str(err), status_code)
            return response.get_response()

        return func(current_user, *args, **kwargs)

    return decorated
