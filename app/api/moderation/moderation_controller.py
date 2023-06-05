import logging
import os
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Dict

import pytz
from flask import Blueprint, make_response, request
from rq import Queue

from app.api.common.wrapper_utils import is_admin, token_required
from app.api.exceptions import ApplicationException
from app.api.moderation.moderation_job import extract_frames, save_file
from app.api.moderation.moderation_service import (
    generate_pdf_report,
    get_by_params,
    get_count_by_params,
    get_monthly_statistics,
    moderate_video,
    start_moderation,
    validate_moderation,
)
from app.dto import BaseResponse, PaginateResponse, UploadInfo, User
from config import DATABASE, UPLOAD_PATH
from redis_worker import conn

logger = logging.getLogger(__name__)
moderation_bp = Blueprint("moderation", __name__)
redis_conn = Queue(connection=conn)


# get moderations by parameters
@moderation_bp.route("/moderations", methods=["GET"])
@token_required
@is_admin
def get_moderation_by_params(_):
    response = PaginateResponse()

    try:
        query_params = request.args.to_dict()

        result, metadata = get_by_params(query_params)
        response.set_metadata_direct(metadata)
        response.set_response(result, HTTPStatus.OK)

    except (Exception, ApplicationException) as err:
        logger.error(str(err))

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    return response.get_response()


# get list of moderations for the current user
@moderation_bp.route("/moderations/user", methods=["GET"])
@token_required
def get_moderation_list(current_user: User):
    response = PaginateResponse()

    try:
        # Get the query parameters from the request as a dictionary and set the user_id and status.exists parameters
        query_params = request.args.to_dict()
        query_params["page"] = request.args.get("page", default=0, type=int)
        query_params["limit"] = request.args.get("limit", default=9999, type=int)
        query_params["sort"] = request.args.get("sort", default="created_at,ASC")
        query_params["user_id"] = str(current_user._id)

        # Get the results
        result, metadata = get_by_params(query_params)
        response.set_metadata_direct(metadata)
        response.set_response(result, HTTPStatus.OK)

    except (Exception, ApplicationException) as err:
        logger.error(str(err))

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    return response.get_response()


# get moderation by ID
@moderation_bp.route("/moderations/<moderation_id>", methods=["GET"])
@token_required
def get_moderation(current_user: User, moderation_id: str):
    response = BaseResponse()

    try:
        # Get the query parameters from the request as a dictionary and set the ID and user_id parameters
        query_params: Dict[str, str] = {}
        query_params["id"] = moderation_id
        query_params["user_id"] = str(current_user._id)

        # Get results. If no moderations were found, raise an ApplicationException with a 404 status
        result, _ = get_by_params(query_params)
        if len(result) == 0:
            raise ApplicationException("Moderasi Tidak Ditemukan", HTTPStatus.NOT_FOUND)
        response.set_response(result[0], HTTPStatus.OK)

    except (Exception, ApplicationException) as err:
        logger.error(str(err))

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )
        response.set_response(str(err), err.status)

    return response.get_response()


# get count of moderations by parameters
@moderation_bp.route("/moderations/count", methods=["GET"])
@token_required
def get_moderation_count(_):
    response = PaginateResponse()

    try:
        query_params = request.args.to_dict()

        count = get_count_by_params(query_params)
        response.set_response(count, HTTPStatus.OK)

    except (Exception, ApplicationException) as err:
        logger.error(str(err))

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    return response.get_response()


# handle moderation form submission
@moderation_bp.route("/moderations", methods=["POST"])
@token_required
def upload_form(current_user: User):
    response = BaseResponse()

    try:
        file = request.files["video_file"]
        form_data = request.form

        # Create an UploadInfo object
        upload_info = UploadInfo(
            user_id=str(current_user._id),
            filename=f"{file.filename.split('.')[0]}",
            file_ext=f"{file.filename.split('.')[1]}",
            file_with_ext=f"{file.filename}",
            video_save_path=os.path.join(
                UPLOAD_PATH, f"{str(current_user._id)}_{file.filename}"
            ),
        )

        # Call the save_file function to save the uploaded file
        upload_info, video_metadata = save_file(upload_info)

        # Enqueue a job to extract frames from the uploaded video
        job = redis_conn.enqueue_call(
            func=extract_frames, args=(upload_info, video_metadata), timeout=1800
        )
        logger.info(
            "Job %s queued || Extracting Frames %s", job.id, upload_info.saved_id
        )

        # If the 'process_now' form data is set to 'true', enqueue a job to analyze the video using models
        if form_data["process_now"] == "true":
            job = redis_conn.enqueue_call(
                func=moderate_video, args=(upload_info, video_metadata), timeout=7200
            )
            logger.info(
                "Job %s queued || Moderating Video %s", job.id, upload_info.saved_id
            )

        # Set the response to indicate that the form was successfully uploaded
        response.set_response(upload_info.saved_id, HTTPStatus.OK)

    except (Exception, ApplicationException) as err:
        logger.error(str(err))

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    return response.get_response()


# handle start moderation
@moderation_bp.route("/moderations/<moderation_id>/start", methods=["PUT"])
@token_required
def initiate_moderation(_, moderation_id):
    response = BaseResponse()
    form_moderation_id = request.form["id"]

    try:
        # Initiate the moderation with the provided ID
        start_moderation(form_moderation_id)
        response.set_response("Moderation Dimulai", HTTPStatus.OK)

    except (Exception, ApplicationException) as err:
        logger.error(str(err))

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    return response.get_response()


# get moderation statistics
@moderation_bp.route("/moderations/statistics", methods=["GET"])
@token_required
def moderation_statistic(_):
    response = BaseResponse()

    try:
        query_params = request.args.to_dict()

        # If no start date is provided, set it to 30 days ago
        if (
            query_params.get("start_date") is None
            or query_params.get("start_date") == ""
        ):
            today = (
                datetime.now()
                .replace(hour=0, minute=0, second=0)
                .astimezone(pytz.timezone("Asia/Jakarta"))
            )
            query_params["start_date"] = today + timedelta(days=-30)

        else:
            # Otherwise, parse the provided start date string into a datetime object
            query_params["start_date"] = (
                datetime.strptime(query_params["start_date"], "%Y-%m-%d")
                .astimezone(pytz.timezone("Asia/Jakarta"))
            )

        # If no end date is provided, set it to the current date and time
        if query_params.get("end_date") is None or query_params.get("end_date") == "":
            query_params["end_date"] = (
                datetime.now()
                .replace(hour=23, minute=59, second=59)
                .astimezone(pytz.timezone("Asia/Jakarta"))
            )
        else:
            # Otherwise, parse the provided end date string into a datetime object
            query_params["end_date"] = (
                datetime.strptime(query_params["end_date"], "%Y-%m-%d")
                .replace(hour=23, minute=59, second=59)
                .astimezone(pytz.timezone("Asia/Jakarta"))
            )

        # Get the monthly statistics for the provided date range
        all_result, detected_result = get_monthly_statistics(
            query_params["start_date"], query_params["end_date"]
        )

        # Set the response data to be the monthly statistics
        response.set_response(
            {"all": all_result, "detected": detected_result}, HTTPStatus.OK
        )
    except (Exception, ApplicationException) as err:
        logger.error(str(err))

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    # Return the response data
    return response.get_response()


# generate a PDF report for a moderation
@moderation_bp.route("/moderations/<moderation_id>/report", methods=["GET"])
@token_required
def generate_report(_, moderation_id):
    try:
        pdf = generate_pdf_report(moderation_id)

        # Create a response object containing the generated PDF
        response = make_response(pdf)

        # Set the headers for the response to indicate that it is a PDF file and provide a filename
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = "inline; filename=output.pdf"
        return response

    except (Exception, ApplicationException) as err:
        logger.error(str(err))

        response = BaseResponse()
        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return response.get_response()


# validate moderation results
@moderation_bp.route("/moderations/<moderation_id>/validate", methods=["PUT"])
@token_required
def validate_result(_, moderation_id):
    response = BaseResponse()

    try:
        moderation_id = request.form["id"]
        result_index = request.form["index"]
        decision = request.form["decision"]

        # Validate the moderation results with the provided ID and decision
        validate_moderation(moderation_id, result_index, decision)
        response.set_response("Dugaan Pelanggaran Divalidasi", HTTPStatus.OK)

    except (Exception, ApplicationException) as err:
        logger.error(str(err))

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response(
                "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
            )

    return response.get_response()
