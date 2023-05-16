import logging
import math
from http import HTTPStatus
from typing import Dict, List

from app.api.common.query_utils import clean_query_params, parse_query_params
from app.dto import PaginateResponse, Pasal, PasalResponse
from config import DATABASE

logger = logging.getLogger(__name__)
PASAL_DB = DATABASE["pasal"]


# ======== Get pasals by params ========
def get_pasal_by_params(query_params: Dict[str, str]) -> List[Dict[str, str]]:
    """
    A function that fetches pasals from the database based on the query parameters provided.

    Args:
    query_params (Dict[str, str]): A dictionary of query parameters.

    Returns:
    List[Dict[str, str]]: A list containing dictionaries of pasals' details.
    """

    response = PaginateResponse()

    try:
        output = []

        # Separating the query parameters into query and pagination parameters
        params, pagination = clean_query_params(query_params)

        # Parsing the query parameters to get the fields to be queried and the sort parameters
        query, sort = parse_query_params(params)

        total_elements = PASAL_DB.count_documents(query)
        # Fetching pasals based on the query parameters, sorting them, and paginating the results
        for pasal in (
            PASAL_DB.find(query)
            .sort(sort["field"], sort["direction"])
            .skip(pagination["limit"] * pagination["page"])
            .limit(pagination["limit"])
        ):
            # Converting the station data to a StationResponse object and adding it to the output list
            res = PasalResponse.from_document(Pasal.from_document(pasal).as_dict())
            output.append(res)

        # Setting the metadata for the response
        response.set_metadata(
            pagination["page"],
            pagination["limit"],
            total_elements,
            math.ceil(total_elements / pagination["limit"]),
        )
        response.set_response(output, HTTPStatus.OK)

    except Exception as err:
        logger.error(err)
        # Setting the response for internal server error
        response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)

    # Returning the response as a list of station dictionaries
    return response.get_response()
