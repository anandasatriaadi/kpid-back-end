import logging
import math
from http import HTTPStatus
from typing import Dict, List, Tuple

from app.api.common.query_utils import clean_query_params, parse_query_params
from app.api.exceptions import ApplicationException
from app.dto import Activity, ActivityResponse, Metadata
from config import DATABASE

logger = logging.getLogger(__name__)
ACTIVITY_DB = DATABASE["activity"]


# Get stations by params
def get_activity_by_params(
    query_params: Dict[str, str]
) -> Tuple[List[ActivityResponse], Metadata]:
    """
    A function that fetches activities from the database based on the query parameters provided.

    Args:
    query_params (Dict[str, str]): A dictionary of query parameters.

    Returns:
    List[Dict[str, str]]: A list containing dictionaries of activities' details.
    """

    try:
        # Clean the query parameters and parse them into query and pagination parameters
        params, pagination = clean_query_params(query_params)
        query, sort = parse_query_params(params)

        total_elements = ACTIVITY_DB.count_documents(query)
        results = ACTIVITY_DB.find(query)
        if len(sort) > 0:
            results = results.sort(sort["field"], sort["direction"])
        if len(pagination) > 0:
            results = results.skip(pagination["limit"] * pagination["page"]).limit(pagination["limit"])

        output: List[ActivityResponse] = []
        # Converting the activity data to a ActivityResponse object
        for activity in results:
            output.append(
                ActivityResponse.from_document(
                    Activity.from_document(activity).as_dict()
                )
            )

        # Setting the metadata for the response
        metadata = Metadata(
            pagination["page"],
            pagination["limit"],
            total_elements,
            math.ceil(total_elements / pagination["limit"]),
        )

        return output, metadata

    except Exception as err:
        logger.error(err)
        # Setting the response for internal server error
        raise ApplicationException(
            "Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR
        )
