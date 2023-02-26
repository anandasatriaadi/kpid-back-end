from http import HTTPStatus
import logging
from flask import request
from controllers.utils import token_required
import os

from config import database
from response.BaseResponse import BaseResponse
from utils.CustomFormatter import init_logging
import ffmpeg

init_logging()
logger = logging.getLogger(__name__)

# ======== POST : login user ========
@token_required
def upload_form(current_user):
    response = BaseResponse()
    try:
        moderation = database["moderation"]
        file = request.files['']
        save_path = os.path.join(f'{os.getcwd()}/uploads', file.filename)
        file.save(save_path)

        all_metadata = read_video_metadata(save_path)
        video_metadata = [data for data in all_metadata if data["codec_type"] == "video"]

        if video_metadata is None:
            response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)
            return response.__dict__, response.status
        
        print(request.form)
        response.set_response(video_metadata, HTTPStatus.OK)
        return response.__dict__, response.status
    except Exception as e:
        logger.error(e)
        response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)
        return response.__dict__, response.status

# ======== READ VIDEO METADATA ========
def read_video_metadata(file_path):
    try:
        print(file_path)
        metadata = ffmpeg.probe(file_path)["streams"]
        return metadata
    except Exception as e:
        logger.error(e)
        return None

