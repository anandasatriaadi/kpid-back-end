import logging
from http import HTTPStatus

from flask import Blueprint, request

from app.api.common.wrapper_utils import is_admin, token_required
from app.api.exceptions import ApplicationException
from app.api.station.station_service import (
    create_station,
    delete_station,
    get_station_by_params,
    update_station,
)
from app.dto import BaseResponse, PaginateResponse

logger = logging.getLogger(__name__)
station_bp = Blueprint("stations", __name__)


# get all stations
@station_bp.route("/stations", methods=["GET"])
@token_required
def get_all_stations(_):
    response = PaginateResponse()
    try:
        # Parse query parameters from the request
        params = {}
        params["page"] = request.args.get("page", default=0, type=int)
        params["limit"] = request.args.get("limit", default=9999, type=int)
        params["sort"] = request.args.get("sort", default="name,ASC")

        # Call the get_user_by_params function with the parsed query parameters and return the response
        results, metadata = get_station_by_params(params)
        response.set_metadata_direct(metadata)
        response.set_response(results, HTTPStatus.OK)
        
    except (Exception, ApplicationException) as err:
        logger.error(str(err))
        
        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)
            
    return response.get_response()


# get all stations
@station_bp.route("/stations", methods=["POST"])
@token_required
@is_admin
def create_new_station(_):
    response = BaseResponse()
    try:
        # Parse form data from the request
        if request.mimetype == "application/json":
            form_data = request.get_json()
        else:
            form_data = request.form

        response.set_response(create_station(form_data.get("station_name")), HTTPStatus.CREATED)

    except (Exception, ApplicationException) as err:
        logger.error(str(err))

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)
            
    return response.get_response()


# get all stations
@station_bp.route("/stations", methods=["PUT"])
@token_required
@is_admin
def update_existing_station(_):
    response = BaseResponse()
    try:
        # Parse query parameters from the request
        if request.mimetype == "application/json":
            form_data = request.get_json()
        else:
            form_data = request.form

        update_station(form_data.get("old_key"), form_data.get("station_name"))
        response.set_response("Station updated successfully", HTTPStatus.OK)

    except (Exception, ApplicationException) as err:
        logger.error(str(err))

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)

    return response.get_response()


# get all stations
@station_bp.route("/stations/<station_key>", methods=["DELETE"])
@token_required
@is_admin
def delete_one_station(_, station_key: str):
    response = BaseResponse()
    try:
        delete_station(station_key)
        response.set_response("Berhasil Menghapus Stasiun", HTTPStatus.OK)

    except (Exception, ApplicationException) as err:
        logger.error(str(err))

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)

    return response.get_response()
