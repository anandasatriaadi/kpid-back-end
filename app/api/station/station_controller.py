import logging
from http import HTTPStatus

from dacite import from_dict
from flask import Blueprint, request

from app.api.common.utils import token_required
from app.api.station.station_service import get_station_by_params
from app.dto import (BaseResponse, CreateUserRequest, LoginUserRequest,
                     UserResponse)

logger = logging.getLogger(__name__)
station_bp = Blueprint('stations', __name__)


# ======== get all stations ========
@station_bp.route('/stations', methods=['GET'])
@token_required
def get_all_stations(_):
    # Parse query parameters from the request
    params = {}
    params["page"] = request.args.get('page', default=0, type=int)
    params["limit"] = request.args.get('limit', default=9999, type=int)
    params["sort"] = request.args.get('sort', default='name,ASC')

    # Call the get_user_by_params function with the parsed query parameters and return the response
    return get_station_by_params(params)
