import logging
import os
from datetime import datetime, timedelta
from http import HTTPStatus

from flask import Blueprint, make_response, request
from pytz import timezone
from rq import Queue

from app.api.common.utils import token_required
from app.api.exceptions import ApplicationException
from app.api.moderation.moderation_service import (cut_video, extract_frames,
                                                   generate_pdf_report,
                                                   get_by_params,
                                                   get_count_by_params,
                                                   get_monthly_statistics,
                                                   save_file, start_moderation)
from app.dto import BaseResponse, PaginateResponse, UploadInfo
from config import UPLOAD_PATH
from redis_worker import conn

logger = logging.getLogger(__name__)
moderation_bp = Blueprint('moderation', __name__)
redis_conn = Queue(connection=conn)


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
    form_data = request.form

    upload_info = UploadInfo(
        user_id=str(current_user["user_id"]),
        filename=f"{file.filename.split('.')[0]}",
        file_ext=f"{file.filename.split('.')[-1]}",
        file_with_ext=f"{file.filename}",
        save_path=os.path.join(
            UPLOAD_PATH, f"{str(current_user['user_id'])}_{file.filename}"),
    )

    upload_info, video_metadata = save_file(upload_info)

    # extract frames from video
    job = redis_conn.enqueue_call(
        func=extract_frames, args=(upload_info, video_metadata))
    logger.info("Job %s started || Extracting Frames %s",
                job.id, upload_info.saved_id)

    # analyze video using models
    if form_data["process_now"] == 'true':
        job = redis_conn.enqueue_call(
            func=cut_video, args=(upload_info, video_metadata))
        logger.info("Job %s started || Cutting Video %s",
                    job.id, upload_info.saved_id)

    response.set_response(upload_info.saved_id, HTTPStatus.OK)
    # response.set_response("Saved", HTTPStatus.OK)
    return response.get_response()


# ======== start moderation ========
@moderation_bp.route('/moderation/start', methods=['PUT'])
@token_required
def initiate_moderation(_):
    response = BaseResponse()
    moderation_id = request.form["id"]

    try:
        start_moderation(moderation_id)
        response.set_response("Moderation Started.", HTTPStatus.OK)
    except ApplicationException as err:
        logger.error(str(err))
        response.set_response(str(err), err.status)
    return response.get_response()


# ======== moderation statistics ========
@moderation_bp.route('/moderation/statistics', methods=['GET'])
@token_required
def moderation_statistic(_):
    response = BaseResponse()

    try:
        query_params = request.args.to_dict()

        if query_params.get("start_date") is None or query_params.get("start_date") == "":
            query_params["start_date"] = datetime.now().astimezone(
                timezone("Asia/Jakarta")) + timedelta(days=-30)
        else:
            query_params["start_date"] = datetime.strptime(
                query_params["start_date"], '%Y-%m-%d').astimezone(timezone("Asia/Jakarta"))

        if query_params.get("end_date") is None or query_params.get("end_date") == "":
            query_params["end_date"] = datetime.now(
            ).astimezone(timezone("Asia/Jakarta"))
        else:
            query_params["end_date"] = datetime.strptime(
                query_params["end_date"], '%Y-%m-%d').astimezone(timezone("Asia/Jakarta"))

        all_result, detected_result = get_monthly_statistics(
            query_params["start_date"], query_params["end_date"])
        response.set_response(
            {"all": all_result, "detected": detected_result}, HTTPStatus.OK)
    except ApplicationException as err:
        logger.error(str(err))
        response.set_response(str(err), err.status)
    return response.get_response()


# ======== moderation statistics ========
@moderation_bp.route('/moderation/report/<moderation_id>', methods=['GET'])
# @token_required
def generate_report(moderation_id):
    pdf = generate_pdf_report(moderation_id)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=output.pdf'
    return response
