import logging
from http import HTTPStatus

from flask import Blueprint, request

from app.api.activity.activity_service import get_activity_by_params
from app.api.common.wrapper_utils import token_required
from app.api.exceptions import ApplicationException
from app.dto import BaseResponse

logger = logging.getLogger(__name__)
activity_bp = Blueprint("activity", __name__)


# ======== get all activities ========
@activity_bp.route("/activity", methods=["GET"])
@token_required
def get_all_activities(_):
    response = BaseResponse()

    try:
        # Get the query parameters from the request
        query_params = request.args.to_dict()
        query_params["page"] = request.args.get("page", default=0, type=int)
        query_params["limit"] = request.args.get("limit", default=9999, type=int)
        query_params["sort"] = request.args.get("sort", default="created_at,ASC")
        logger.error(query_params)

        # Get the monthly statistics for the provided date range
        result, metadata = get_activity_by_params(query_params)

        # Set the response data to be the monthly statistics
        response.set_response(result, HTTPStatus.OK)

    except ApplicationException as err:
        raise (err)
        # Log any application exceptions and set the response data to be the exception message and status
        logger.error(str(err))
        response.set_response(str(err), err.status)

    # Return the response data
    return response.get_response()
