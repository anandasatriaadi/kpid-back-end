import logging

from flask import Blueprint, request

from app.api.common.wrapper_utils import is_admin, token_required
from app.api.station.station_service import (
    create_station,
    delete_station,
    get_station_by_params,
    update_station,
)

logger = logging.getLogger(__name__)
station_bp = Blueprint("stations", __name__)


# ======== get all stations ========
@station_bp.route("/stations", methods=["GET"])
@token_required
def get_all_stations(_):
    # Parse query parameters from the request
    params = {}
    params["page"] = request.args.get("page", default=0, type=int)
    params["limit"] = request.args.get("limit", default=9999, type=int)
    params["sort"] = request.args.get("sort", default="name,ASC")

    # Call the get_user_by_params function with the parsed query parameters and return the response
    return get_station_by_params(params)


# ======== get all stations ========
@station_bp.route("/stations", methods=["POST"])
@token_required
@is_admin
def create_new_station(_):
    # Parse form data from the request
    if request.mimetype == "application/json":
        form_data = request.get_json()
    else:
        form_data = request.form

    # Call the create_station function with the parsed form data and return the response
    return create_station(form_data.get("station_name"))


# ======== get all stations ========
@station_bp.route("/stations", methods=["PUT"])
@token_required
@is_admin
def update_existing_station(_):
    # Parse query parameters from the request
    if request.mimetype == "application/json":
        form_data = request.get_json()
    else:
        form_data = request.form

    # Call the update_station function with the parsed form data and return the response
    return update_station(form_data.get("old_key"), form_data.get("station_name"))

# ======== get all stations ========
@station_bp.route("/stations/<station_key>", methods=["DELETE"])
@token_required
@is_admin
def delete_one_station(_, station_key: str):
    # Call the delete_one_station function with the station key and return the response
    return delete_station(station_key)
