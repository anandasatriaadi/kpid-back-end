import logging
import math
from dataclasses import asdict
from http import HTTPStatus
from typing import Dict, List, Tuple

from app.api.common.query_utils import clean_query_params, parse_query_params
from app.api.common.string_utils import tokenize_string
from app.api.exceptions import ApplicationException
from app.dto import (
    CreateStationRequest,
    Metadata,
    Station,
    StationResponse,
    UpdateStationRequest,
)
from config import DATABASE

logger = logging.getLogger(__name__)
STATION_DB = DATABASE["stations"]


# Get stations by params
def get_station_by_params(
    query_params: Dict[str, str]
) -> Tuple[List[StationResponse], Metadata]:
    """
    A function that fetches stations from the database based on the query parameters provided.

    Args:
    query_params (Dict[str, str]): A dictionary of query parameters.

    Returns:
    Tuple[List[StationResponse], Metadata]: A list containing dictionaries of stations' details.
    """

    output = []

    # Separating the query parameters into query and pagination parameters
    params, pagination = clean_query_params(query_params)
    query, sort = parse_query_params(params)
    total_elements = STATION_DB.count_documents(query)
    results = STATION_DB.find(query)
    if len(sort) > 0:
        results = results.sort(sort["field"], sort["direction"])
    if len(pagination) > 0:
        results = results.skip(pagination["limit"] * pagination["page"]).limit(pagination["limit"])

    # Fetching stations based on the query parameters, sorting them, and paginating the results
    for station in results:
        # Converting the station data to a StationResponse Object and adding it to the output list
        res = StationResponse.from_document(Station.from_document(station).as_dict())
        output.append(res)

    # Setting the metadata for the response
    metadata = Metadata(
        pagination["page"],
        pagination["limit"],
        total_elements,
        math.ceil(total_elements / pagination["limit"]),
    )

    return output, metadata


# Create station
def create_station(station_name: str) -> str:
    """
    A function that creates a new station in the database with the details provided in the CreateStationRequest object.

    Args:
    station_name (str): String of the new station name.

    Returns:
    str: A string of inserted document id
    """

    # Checking if the station already exists in the database
    name_tokenized = tokenize_string(station_name, True)
    station_res = STATION_DB.find_one({"key": name_tokenized})

    if not station_res:
        # Create new station request
        create_request = CreateStationRequest(key=name_tokenized, name=station_name)

        # Inserting the new station details into the database
        res = STATION_DB.insert_one(asdict(create_request))

        # Setting the response for successful station creation
        return str(res.inserted_id)
    else:
        raise ApplicationException("Station already exists", HTTPStatus.BAD_REQUEST)


def update_station(old_key: str, station_name: str) -> int:
    """
    A function that updates an existing station in the database with the details provided in the UpdateStationRequest object.

    Args:
    old_key (str): String of the existing key.
    station_name (str): String of the existing station name.

    Returns:
    int: A number of stations modified.
    """

    # Checking if the station exists in the database
    old_key_tokenized = tokenize_string(old_key, True)
    new_key_tokenized = tokenize_string(station_name, True)
    station_res = STATION_DB.find_one({"key": old_key_tokenized})

    if station_res:
        # Update existing station details
        update_request = UpdateStationRequest(key=new_key_tokenized, name=station_name)
        res = STATION_DB.update_one(
            {"key": old_key_tokenized}, {"$set": asdict(update_request)}
        )
        return res.modified_count
    else:
        raise ApplicationException("Station does not exist", HTTPStatus.BAD_REQUEST)


def delete_station(
    key: str,
) -> int:
    # Checking if the station exists in the database
    station_res = STATION_DB.find_one({"key": key})

    if station_res:
        # Delete the station from the database
        res = STATION_DB.delete_one({"key": key})
        return res.deleted_count
    else:
        raise ApplicationException("Station does not exist", HTTPStatus.BAD_REQUEST)
