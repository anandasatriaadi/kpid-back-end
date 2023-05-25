import logging
from http import HTTPStatus

from flask import Blueprint, request

from app.api.common.wrapper_utils import token_required
from app.api.exceptions import ApplicationException
from app.api.pasal.pasal_service import get_pasal_by_params
from app.dto import PaginateResponse

logger = logging.getLogger(__name__)
pasal_bp = Blueprint("pasals", __name__)


# get all stations
@pasal_bp.route("/pasals", methods=["GET"])
@token_required
def get_all_pasals(_):
    response = PaginateResponse()

    try:
        # Parse query parameters from the request
        params = {}
        params["page"] = request.args.get("page", default=0, type=int)
        params["limit"] = request.args.get("limit", default=9999, type=int)
        params["sort"] = request.args.get("sort", default="name,ASC")

        # Call the get_user_by_params function with the parsed query parameters and return the response
        result, metadata = get_pasal_by_params(params)
        response.set_metadata_direct(metadata)
        response.set_response(result, HTTPStatus.OK)

    except (Exception, ApplicationException) as err:
        logger.error(err)

        if isinstance(err, ApplicationException):
            response.set_response(str(err), err.status)
        else:
            response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)

    return response.get_response()