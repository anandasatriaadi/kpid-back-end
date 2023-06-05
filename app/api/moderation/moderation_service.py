import logging
import math
import os
from datetime import datetime
from http import HTTPStatus
from typing import Dict, List, Tuple

import pdfkit
import pytz
from babel.dates import format_datetime
from bson.objectid import ObjectId
from rq import Queue

from app.api.common.query_utils import clean_query_params, parse_query_params
from app.api.exceptions import ApplicationException
from app.api.moderation.moderation_job import generate_html_tags, moderate_video
from app.dto import (
    CreateModerationRequest,
    Metadata,
    Moderation,
    ModerationDecision,
    ModerationResponse,
    ModerationStatus,
    Station,
    UploadInfo,
)
from config import DATABASE, GOOGLE_BUCKET_NAME, GOOGLE_STORAGE_CLIENT, UPLOAD_PATH
from redis_worker import conn

# Initializations
logger = logging.getLogger(__name__)
redis_conn = Queue(connection=conn)
MODERATION_DB = DATABASE["moderation"]
STATION_DB = DATABASE["stations"]


# Returns A Paginateresponse Containing A List Of ModerationResponses Based On The Provided Query Parameters
def get_by_params(
    query_params: Dict[str, str]
) -> Tuple[List[ModerationResponse], Metadata]:
    moderation = DATABASE["moderation"]

    # Clean The Query Parameters And Parse Them Into Query And Pagination Parameters
    params, pagination = clean_query_params(query_params)
    query, sort = parse_query_params(params)

    # Get The Total Number Of Elements Matching The Query
    total_elements = moderation.count_documents(query)

    results = None

    # If There Are Sort Fields, Sort The Results Based On The Specified Field And Direction
    results = moderation.find(query)
    if len(sort) > 0:
        results = results.sort(sort["field"], sort["direction"])
    if len(pagination) > 0:
        results = results.skip(pagination["limit"] * pagination["page"]).limit(
            pagination["limit"]
        )

    # Convert The MongoDB Results Into ModerationResponse Objects And Add Them To The Output List
    output: List[ModerationResponse] = []
    for result in results:
        output.append(ModerationResponse.from_document(result))

    # Set The Metadata For The Response If There Are Pagination Parameters
    metadata = None
    if len(pagination) > 0:
        metadata = Metadata(
            pagination["page"],
            pagination["limit"],
            total_elements,
            math.ceil(total_elements / pagination["limit"]),
        )

    return output, metadata


# Get Count By Params
def get_count_by_params(query_params: dict) -> int:
    moderation = DATABASE["moderation"]

    params, _ = clean_query_params(query_params)
    query, _ = parse_query_params(params)

    return moderation.count_documents(query)


# Start The Moderation Process For The Provided Moderation ID
def start_moderation(object_id: str):
    # Retrieve The ModerationResponse Object For The Provided ID From The MongoDB Database
    moderation = Moderation.from_document(
        MODERATION_DB.find_one({"_id": ObjectId(object_id)})
    )

    # If The Moderation Cannot Be Found, Raise A 404 Exception
    if moderation is None:
        raise ApplicationException("Moderasi Tidak Ditemukan", HTTPStatus.NOT_FOUND)

    # If The Moderation Is Not In The Required Status, Raise A 400 Exception
    if moderation.status != str(ModerationStatus.UPLOADED):
        raise ApplicationException(
            "Moderasi Tidak Berada pada Status yang Diperlukan", HTTPStatus.BAD_REQUEST
        )

    # Create An UploadInfo Object For The Moderation's File
    upload_info = UploadInfo(
        saved_id=str(moderation._id),
        user_id=str(moderation.user_id),
        filename=moderation.filename.split(".")[0],
        file_ext=moderation.filename.split(".")[-1],
        file_with_ext=moderation.filename,
        video_save_path=os.path.join(
            UPLOAD_PATH, f"{moderation.user_id}_{moderation.filename}"
        ),
    )

    # Create A Video Metadata List With The Duration Of The Moderation
    video_metadata = [{"duration": moderation.duration}]

    # Enqueue A Job To Moderate The Video Using The Provided UploadInfo And Video Metadata
    job = redis_conn.enqueue_call(
        func=moderate_video, args=(upload_info, video_metadata), timeout=7200
    )

    # Log The ID Of The Job And The Saved ID Of The UploadInfo Object For Debugging Purposes
    logger.info("Job %s queued || Moderating Video %s", job.id, upload_info.saved_id)

    return True


# Monthly Statistics
def get_monthly_statistics(start_date: str, end_date: str) -> Tuple[dict, dict]:
    # Define A MongoDB Query Pipeline To Group All Moderations By Date And Count The Number Of Moderations On Each Date
    all_moderation_query = [
        {"$match": {"$and": [{"created_at": {"$gte": start_date, "$lte": end_date}}]}},
        {
            "$addFields": {
                "stringDate": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                }
            }
        },
        {"$group": {"_id": "$stringDate", "count": {"$count": {}}}},
    ]

    # Define A MongoDB Query Pipeline To Group Detected Moderations By Date And Count The Number Of Detected Moderations On Each Date
    detected_moderation_query = [
        {
            "$match": {
                "$and": [
                    {"result.0": {"$exists": "true"}},
                    {"created_at": {"$gte": start_date, "$lte": end_date}},
                ]
            }
        },
        {
            "$addFields": {
                "stringDate": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                }
            }
        },
        {"$group": {"_id": "$stringDate", "count": {"$count": {}}}},
    ]

    # Execute The All Moderation Query Pipeline And Store The Results In A List
    all_results = MODERATION_DB.aggregate(all_moderation_query)
    parse_all_results = []
    for result in all_results:
        parse_all_results.append(result)

    # Execute The Detected Moderation Query Pipeline And Store The Results In A List
    detected_results = MODERATION_DB.aggregate(detected_moderation_query)
    parse_detected_results = []
    for result in detected_results:
        parse_detected_results.append(result)

    # Return A Tuple Containing The Parsed Results For All Moderations And Detected Moderations
    return parse_all_results, parse_detected_results


# Generate A PDF Report For The Moderation With The Provided Moderation ID
def generate_pdf_report(moderation_id):
    # Retrieve The ModerationResponse Object For The Provided ID From The MongoDB Database
    result = MODERATION_DB.find_one({"_id": ObjectId(moderation_id)})
    moderation = ModerationResponse.from_document(result)

    # Get The HTML Template For The PDF Report From A Local File
    template_path = os.path.join("app", "template", "letter.html")
    with open(template_path, "r") as file:
        html = file.read()

    # Generate HTML Tags For The Moderation's Result Data
    html_results = generate_html_tags(moderation.result)

    # Replace Placeholders In The HTML Template With Data From The Moderation
    html = html.replace(
        "{{current_date}}",
        format_datetime(
            datetime.now(pytz.timezone("Asia/Jakarta")), "d MMMM YYYY", locale="id_ID"
        ),
    )
    html = html.replace(
        "{{record_date}}",
        format_datetime(moderation.recording_date, "d MMMM YYYY", locale="id_ID"),
    )
    html = html.replace("{{start_time}}", moderation.start_time)
    if isinstance(moderation.station_name, dict):
        station = Station.from_document(moderation.station_name)
        html = html.replace("{{station_name}}", station.name)
    else:
        html = html.replace("{{station_name}}", moderation.station_name)
    html = html.replace("{{program_name}}", moderation.program_name)
    html = html.replace("{{results}}", html_results)

    # Generate A Pdf File From The HTML Template Using PDFkit
    pdf = pdfkit.from_string(html, False)

    return pdf


# Generate HTML Tags For The Moderation's Result Data
def validate_moderation(moderation_id, result_index, decision):
    # Retrieve The ModerationResponse Object For The Provided ID From The MongoDB Database
    result = MODERATION_DB.find_one({"_id": ObjectId(moderation_id)})
    moderation = ModerationResponse.from_document(result)
    moderation_results = moderation.result
    is_all_moderated = True
    for index, result in enumerate(moderation_results):
        if index == int(result_index):
            result["decision"] = str(
                ModerationDecision.VALID
                if decision == "VALID"
                else ModerationDecision.INVALID
            )

            if result["decision"] == str(ModerationDecision.PENDING):
                is_all_moderated = False

    logger.error(moderation_results)
    # Update The Status Of The Moderation In The Database To The Provided Decision
    update_data = (
        {"result": moderation_results, "status": str(ModerationStatus.VALIDATED)}
        if is_all_moderated
        else {"result": moderation_results}
    )
    MODERATION_DB.update_one({"_id": ObjectId(moderation_id)}, {"$set": update_data})

    return True
