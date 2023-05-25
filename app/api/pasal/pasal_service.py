import logging
import math
from typing import Dict, List, Tuple

from app.api.common.query_utils import clean_query_params, parse_query_params
from app.dto import Metadata, Pasal, PasalResponse
from config import DATABASE

logger = logging.getLogger(__name__)
PASAL_DB = DATABASE["pasal"]


# Get pasals by params
def get_pasal_by_params(query_params: Dict[str, str]) -> Tuple[List[PasalResponse], Metadata]:
    """
    A function that fetches pasals from the database based on the query parameters provided.

    Args:
    query_params (Dict[str, str]): A dictionary of query parameters.

    Returns:
    List[Dict[str, str]]: A list containing dictionaries of pasals' details.
    """

    output = []

    # Separating the query parameters into query and pagination parameters
    params, pagination = clean_query_params(query_params)

    # Parsing the query parameters to get the fields to be queried and the sort parameters
    query, sort = parse_query_params(params)

    total_elements = PASAL_DB.count_documents(query)
    results = PASAL_DB.find(query)
    if len(sort) > 0:
        results = results.sort(sort["field"], sort["direction"])
    if len(pagination) > 0:
        results = results.skip(pagination["limit"] * pagination["page"]).limit(pagination["limit"])
    # Fetching pasals based on the query parameters, sorting them, and paginating the results
    for pasal in results:
        # Converting the station data to a StationResponse object and adding it to the output list
        res = PasalResponse.from_document(Pasal.from_document(pasal).as_dict())
        output.append(res)

    # Setting the metadata for the response
    metadata = Metadata(
        pagination["page"],
        pagination["limit"],
        total_elements,
        math.ceil(total_elements / pagination["limit"]),
    )
    
    return output, metadata
