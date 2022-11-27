from http import HTTPStatus
import logging
from flask import request
from controllers.utils import token_required
from datetime import datetime, timedelta

from config import database
from response.BaseResponse import BaseResponse
from response.form.FormResponse import FormResponse
from utils.CustomFormatter import init_logging

init_logging()
logger = logging.getLogger(__name__)

# ======== POST : login user ========
@token_required
def upload_form(current_user):
    response = BaseResponse()
    try:
        moderation = database["moderation"]
        print(request.files)
        print(request.form)
        # email = request.form.get('email')
        # password = request.form.get('password')
        # user_res = users.find_one({'email' : email})
        # logger.info(request.form.keys())
        # if user_res:
        #     if check_password_hash(user_res['password'], password):
        #         access_token = jwt.encode({
        #             'name': user_res['name'],
        #             'email': user_res['email'],
        #             'exp' : datetime.utcnow() + timedelta(minutes = 30)
        #         }, SECRET_KEY, algorithm="HS256")
        #         user_res.pop('_id')
        #         user_res.pop('password')
        #         response.setResponse({"token": access_token, "user_data": user_res}, HTTPStatus.OK)
        #     else:
        #         response.setResponse("Invalid username and password", HTTPStatus.BAD_REQUEST)
        # else:
        #     response.setResponse("No results found", HTTPStatus.NOT_FOUND)
        response.setResponse("No results found", HTTPStatus.NOT_FOUND)
        return response.__dict__, response.status
    except Exception as e:
        logger.error(e)
        response.setResponse("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)
        return response.__dict__, response.status