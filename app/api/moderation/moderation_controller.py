import logging
import os
import threading
from http import HTTPStatus

from flask import Blueprint, request

from app.api.common.utils import token_required
from app.api.exceptions import ApplicationException
from app.api.moderation.moderation_service import (cut_video, extract_frames,
                                                   get_by_params,
                                                   get_count_by_params,
                                                   save_file)
from app.dto import (BaseResponse, PaginateResponse,
                     UploadInfo)
from config import UPLOAD_PATH

logger = logging.getLogger(__name__)
moderation_bp = Blueprint('moderation', __name__)


# ======== get moderation by params ========
@moderation_bp.route('/moderation', methods=['GET'])
@token_required
def get_moderation_by_params(_):
    response = PaginateResponse()
    try:
        query_params = request.args.to_dict()
        response = get_by_params(query_params)
    except ApplicationException as err:
        logger.error(str(err))
        response.set_response(str(err), err.status)
    return response.get_response()

# ======== get moderation list of user ========


@moderation_bp.route('/moderation-list', methods=['GET'])
@token_required
def get_moderation_list(current_user):
    response = PaginateResponse()
    try:
        query_params = request.args.to_dict()
        query_params["user_id"] = current_user["user_id"]
        query_params["status.exists"] = "true"
        response = get_by_params(query_params)
    except ApplicationException as err:
        logger.error(str(err))
        response.set_response(str(err), err.status)
    return response.get_response()


# ======== get single moderation data ========
@moderation_bp.route('/moderation/<moderation_id>', methods=['GET'])
@token_required
def get_moderation(current_user, moderation_id):
    response = BaseResponse()
    try:
        query_params = request.args.to_dict()
        query_params["id"] = moderation_id
        query_params["user_id"] = current_user["user_id"]
        result = get_by_params(query_params)
        if len(result.data) == 0:
            raise ApplicationException(
                "No moderation found", HTTPStatus.NOT_FOUND)
        response.set_response(result.data[0], HTTPStatus.OK)
    except ApplicationException as err:
        logger.error(str(err))
        response.set_response(str(err), err.status)
    return response.get_response()


# ======== get moderation by params ========
@moderation_bp.route('/moderation/count', methods=['GET'])
@token_required
def get_moderation_count_by_params(_):
    response = PaginateResponse()
    try:
        query_params = request.args.to_dict()
        count = get_count_by_params(query_params)
        response.set_response(count, HTTPStatus.OK)
    except ApplicationException as err:
        logger.error(str(err))
        response.set_response(str(err), err.status)
    return response.get_response()


# ======== upload moderation form ========
@moderation_bp.route('/moderation-form', methods=['POST'])
@token_required
def upload_form(current_user):
    response = BaseResponse()
    file = request.files['video_file']
    upload_info = UploadInfo(
        user_id=str(current_user["user_id"]),
        filename=f"{file.filename.split('.')[0]}",
        file_ext=f"{file.filename.split('.')[-1]}",
        file_with_ext=f"{file.filename}",
        save_path=os.path.join(
            UPLOAD_PATH, f"{str(current_user['user_id'])}_{file.filename}"),
    )

    upload_info, video_metadata = save_file(upload_info)

    threading.Thread(target=extract_frames, args=(
        upload_info, video_metadata)).start()
    threading.Thread(target=cut_video, args=(
        upload_info, video_metadata)).start()

    response.set_response(upload_info.saved_id, HTTPStatus.OK)
    return response.get_response()
