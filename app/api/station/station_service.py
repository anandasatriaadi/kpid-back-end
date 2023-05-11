import logging
import math
from dataclasses import asdict
from http import HTTPStatus
from typing import Dict, List, Tuple

from dacite import from_dict

from app.api.common.query_utils import clean_query_params, parse_query_params
from app.api.common.string_utils import tokenize_string
from app.dto import (BaseResponse, CreateStationRequest, PaginateResponse,
                     Station, StationResponse, UpdateStationRequest)
from config import DATABASE

logger = logging.getLogger(__name__)
STATION_DB = DATABASE["stations"]

# ======== Get stations by params ========
def get_station_by_params(query_params: Dict[str, str]) -> Tuple[List[Dict[str, str]], HTTPStatus]:
    """
    A function that fetches stations from the database based on the query parameters provided.

    Args:
    query_params (Dict[str, str]): A dictionary of query parameters.

    Returns:
    List[Dict[str, str]]: A list containing dictionaries of stations' details.
    """

    response = PaginateResponse()

    try:
        output = []
        total_elements = STATION_DB.count_documents({})

        # Separating the query parameters into query and pagination parameters
        params, pagination = clean_query_params(query_params)

        # Parsing the query parameters to get the fields to be queried and the sort parameters
        query, sort = parse_query_params(params)

        # Fetching stations based on the query parameters, sorting them, and paginating the results
        for station in STATION_DB.find(query).sort(sort["field"], sort["direction"]).skip(pagination["limit"] * pagination["page"]).limit(pagination["limit"]):
            # Converting the station data to a StationResponse object and adding it to the output list
            res = StationResponse.from_document(Station.from_document(station).as_dict())
            output.append(res)

        # Setting the metadata for the response
        response.set_metadata(pagination["page"], pagination["limit"], total_elements, math.ceil(total_elements/pagination["limit"]))
        response.set_response(output, HTTPStatus.OK)

    except Exception as err:
        logger.error(err)
        # Setting the response for internal server error
        response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)

    # Returning the response as a list of station dictionaries
    return response.get_response()


# ======== Create station ========
def create_station(station_name: str) -> Tuple[Dict[str, str], HTTPStatus]:
    """
    A function that creates a new station in the database with the details provided in the CreateStationRequest object.

    Args:
    station_name (str): String of the new station name.

    Returns:
    Tuple[Dict[str, str], HTTPStatus]: A dictionary containing the response message and HTTP status code.
    """

    response = BaseResponse()

    try:
        # Checking if the station already exists in the database
        name_tokenized = tokenize_string(station_name, True) 
        station_res = STATION_DB.find_one({"key": name_tokenized})
        if station_res:
            response.set_response("Station already exists", HTTPStatus.BAD_REQUEST)
        else:
            # Create new station request
            create_request = CreateStationRequest(key=name_tokenized, name=station_name)

            # Inserting the new station details into the database
            res = STATION_DB.insert_one(asdict(create_request))

            # Setting the response for successful station creation
            response.set_response(str(res.inserted_id), HTTPStatus.CREATED)

    except Exception as err:
        logger.error(err)
        # Setting the response for internal server error
        response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)

    # Returning the response as a dictionary
    return response.get_response()


def update_station(old_key: str, station_name: str) -> Tuple[Dict[str, str], HTTPStatus]:
    """
    A function that updates an existing station in the database with the details provided in the UpdateStationRequest object.

    Args:
    old_key (str): String of the existing key.
    station_name (str): String of the existing station name.

    Returns:
    Tuple[Dict[str, str], HTTPStatus]: A dictionary containing the response message and HTTP status code.
    """

    response = BaseResponse()

    try:
        # Checking if the station exists in the database
        old_key_tokenized = tokenize_string(old_key, True)
        new_key_tokenized = tokenize_string(station_name, True)
        station_res = STATION_DB.find_one({"key": old_key_tokenized})

        if station_res:
            # Update existing station details
            update_request = UpdateStationRequest(key=new_key_tokenized, name=station_name)
            res = STATION_DB.update_one({"key": old_key_tokenized}, {"$set": asdict(update_request)})
            response.set_response(str(res.modified_count) + " station updated", HTTPStatus.OK)
        else:
            response.set_response("Station not found", HTTPStatus.BAD_REQUEST)

    except Exception as err:
        logger.error(err)
        # Setting the response for internal server error
        response.set_response("Internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)

    # Returning the response as a dictionary
    return response.get_response()