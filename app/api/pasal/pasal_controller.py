import logging

from flask import Blueprint, request

from app.api.common.wrapper_utils import token_required
from app.api.pasal.pasal_service import get_pasal_by_params

logger = logging.getLogger(__name__)
pasal_bp = Blueprint('pasals', __name__)


# ======== get all stations ========
@pasal_bp.route('/pasals', methods=['GET'])
@token_required
def get_all_pasals(_):
    # Parse query parameters from the request
    params = {}
    params["page"] = request.args.get('page', default=0, type=int)
    params["limit"] = request.args.get('limit', default=9999, type=int)
    params["sort"] = request.args.get('sort', default='name,ASC')

    # Call the get_user_by_params function with the parsed query parameters and return the response
    return get_pasal_by_params(params)

