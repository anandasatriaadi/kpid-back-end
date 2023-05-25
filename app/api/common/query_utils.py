import logging
from datetime import datetime
from http import HTTPStatus
from typing import Dict, Tuple

from bson.objectid import ObjectId
from pymongo import ASCENDING, DESCENDING
from pytz import timezone

from app.api.exceptions import ApplicationException

logger = logging.getLogger(__name__)


def clean_query_params(
    query_params: Dict[str, str]
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    A function that processes a dictionary of query parameters and separates them into two dictionaries:
    one for pagination parameters and one for query parameters.

    Args:
    query_params (Dict[str, str]): A dictionary of query parameters.

    Returns:
    Tuple[Dict[str, str], Dict[str, str]]: A tuple containing two dictionaries: one for query parameters and one for pagination parameters.

    Example usage:
    query, pagination = clean_query_params(query_params)
    """

    # Initializing empty dictionaries for query parameters and pagination parameters
    query = {}
    pagination = {}

    # Iterating over each key-value pair in the query_params dictionary
    for key, value in query_params.items():
        # If the key is "page" or "limit", convert the value to an integer and add it to the pagination dictionary
        if key == "page" or key == "limit":
            pagination[key] = int(value)
        # Otherwise, add the key-value pair to the query dictionary
        else:
            query[key] = value

    # Returning a tuple containing the query dictionary and the pagination dictionary
    return query, pagination


def parse_query_params(
    query_params: Dict[str, str]
) -> Tuple[Dict[str, any], Dict[str, int]]:
    """
    A function that parses the query parameters and separates them into criteria for querying the database and sorting parameters.

    Args:
    query_params (Dict[str, str]): A dictionary of query parameters.

    Returns:
    Tuple[Dict[str, Any], Dict[str, int]]: A tuple containing a dictionary of query criteria and a dictionary of sorting parameters.

    Example usage:
    criteria, sorting = parse_query_params(query_params)
    """

    supported_operators = {
        "in": __handle_in_operator,
        "nin": __handle_nin_operator,
        "gt": __handle_gt_operator,
        "gte": __handle_gte_operator,
        "lt": __handle_lt_operator,
        "lte": __handle_lte_operator,
        "exists": __handle_exists_operator,
    }

    criteria, sorting = {}, {}
    for key, value in query_params.items():
        key_parts = key.split(".")
        if len(key_parts) == 1:
            field, operator = key, None
        else:
            field_parts, operator = key_parts[:-1], key_parts[-1]
            field = ".".join(field_parts)

        # Checking if the operator is supported, and calling the corresponding function
        if operator and operator not in supported_operators:
            raise ApplicationException(
                f"Unsupported operator: {operator}", HTTPStatus.BAD_REQUEST
            )

        if operator in supported_operators:
            field = "_id" if field == "id" else field
            criteria[field] = criteria.get(field, [])
            supported_operators[operator](criteria, field, value)
        elif key == "sort":
            field, order = value.split(",")
            sorting["field"] = field
            sorting["direction"] = ASCENDING if order == "ASC" else DESCENDING
        else:
            field = "_id" if field == "id" else field
            criteria[field] = criteria.get(field, [])
            __handle_default_operator(criteria, field, value)

    temp = []
    for field, values in criteria.items():
        for value in values:
            temp.append({field: value})

    criteria = {"$and": temp} if len(temp) >= 1 else {}
    return criteria, sorting


def __handle_list_operator(
    criteria: Dict[str, any], field: str, value: str, operator: str
):
    criteria[field].append({operator: value.split(",")})


def __handle_date_operator(
    criteria: Dict[str, any],
    field: str,
    value: str,
    operator: str,
    hour: int,
    minute: int,
    second: int,
):
    try:
        value = datetime.strptime(value, "%Y-%m-%d").replace(
            hour=hour, minute=minute, second=second
        )
    except ValueError:
        pass
    criteria[field].append({operator: value})


def __handle_in_operator(criteria, field, value):
    __handle_list_operator(criteria, field, value, "$in")


def __handle_nin_operator(criteria, field, value):
    __handle_list_operator(criteria, field, value, "$nin")


def __handle_gt_operator(criteria, field, value):
    __handle_date_operator(criteria, field, value, "$gt", 0, 0, 0)


def __handle_gte_operator(criteria, field, value):
    __handle_date_operator(criteria, field, value, "$gte", 0, 0, 0)


def __handle_lt_operator(criteria, field, value):
    __handle_date_operator(criteria, field, value, "$lt", 23, 59, 59)


def __handle_lte_operator(criteria, field, value):
    __handle_date_operator(criteria, field, value, "$lte", 23, 59, 59)


def __handle_exists_operator(criteria: Dict[str, any], field: str, value: str):
    criteria[field].append({"$exists": value.lower() == "true"})


def __handle_default_operator(criteria: Dict[str, any], field: str, value: str):
    if field == "_id":
        value = ObjectId(value)
        criteria[field].append(value)
    else:
        criteria[field].append({"$eq": value})
