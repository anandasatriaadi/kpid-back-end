from flask import request
import logging
import jwt
from functools import wraps
from config import database, SECRET_KEY
from response.BaseResponse import BaseResponse
from utils.CustomFormatter import init_logging

init_logging()
logger = logging.getLogger(__name__)

def token_required(f):
    @wraps(f)
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
            return response.__dict__, response.status

        try:
            # decoding the payload to fetch the stored details
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = database["users"].find_one({"email": data["email"]})
        except jwt.ExpiredSignatureError as e:
            response.set_response("Token is expired", 401)
            return response.__dict__, response.status
        except Exception as e:
            logger.error(e)
            response.set_response("Token is invalid", 401)
            return response.__dict__, response.status
        # returns the current logged in users contex to the routes
        return f(current_user, *args, **kwargs)

    return decorated