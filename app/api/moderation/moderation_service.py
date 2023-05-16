import logging
import math
import os
import random
from datetime import datetime, timedelta
from http import HTTPStatus
from json import loads
from typing import Dict, Tuple

import ffmpeg
import pdfkit
import pytz
import requests
from babel.dates import format_datetime
from bson.objectid import ObjectId
from flask import request
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from rq import Queue

from app.api.common.query_utils import clean_query_params, parse_query_params
from app.api.common.string_utils import tokenize_string
from app.api.exceptions import ApplicationException
from app.api.station.station_service import create_station
from app.dto import (
    CreateModerationRequest,
    ModerationDecision,
    ModerationResponse,
    ModerationStatus,
    PaginateResponse,
    Station,
    UploadInfo,
)
from config import (
    DATABASE,
    GOOGLE_BUCKET_NAME,
    GOOGLE_EXTRACT_FRAME_URL,
    GOOGLE_STORAGE_CLIENT,
    UPLOAD_PATH,
)
from redis_worker import conn

# ======== INITIALIZATIONS ========
logger = logging.getLogger(__name__)
redis_conn = Queue(connection=conn)
MODERATION_DB = DATABASE["moderation"]
STATION_DB = DATABASE["stations"]


# ======== returns a PaginateResponse containing a list of ModerationResponses based on the provided query parameters ========
def get_by_params(query_params: Dict[str, str]) -> PaginateResponse:
    response = PaginateResponse()
    moderation = DATABASE["moderation"]

    # Clean the query parameters to remove any invalid or unnecessary values
    params, pagination = clean_query_params(query_params)

    # Parse the cleaned query parameters into a MongoDB query and sort fields
    query, sort = parse_query_params(params)

    output = []

    # Get the total number of elements matching the query
    total_elements = moderation.count_documents(query)

    results = None

    # If there are sort fields, sort the results based on the specified field and direction
    if len(sort) > 0:
        if len(pagination) > 0:
            # If there are pagination parameters, limit the number of results returned based on the provided page and limit
            results = (
                moderation.find(query)
                .sort(sort["field"], sort["direction"])
                .skip(pagination["limit"] * pagination["page"])
                .limit(pagination["limit"])
            )
        else:
            # If there are no pagination parameters, return all results sorted based on the specified field and direction
            results = moderation.find(query).sort(sort["field"], sort["direction"])
    else:
        if len(pagination) > 0:
            # If there are pagination parameters, limit the number of results returned based on the provided page and limit
            results = (
                moderation.find(query)
                .skip(pagination["limit"] * pagination["page"])
                .limit(pagination["limit"])
            )
        else:
            # If there are no pagination parameters, return all results
            results = moderation.find(query)

    # Convert the MongoDB results into ModerationResponse objects and add them to the output list
    for result in results:
        output.append(ModerationResponse.from_document(result))

    # Set the metadata for the response if there are pagination parameters
    if len(pagination) > 0:
        response.set_metadata(
            pagination["page"],
            pagination["limit"],
            total_elements,
            math.ceil(total_elements / pagination["limit"]),
        )

    # Set the response data to the output list with a 200 status code
    response.set_response(output, HTTPStatus.OK)

    return response


# ======== get count by params ========
def get_count_by_params(query_params: dict) -> int:
    moderation = DATABASE["moderation"]

    params, _ = clean_query_params(query_params)
    query, _ = parse_query_params(params)

    return moderation.count_documents(query)


# ======== read video metadata ========
def read_video_metadata(file_path):
    try:
        metadata = ffmpeg.probe(file_path)["streams"]
        return metadata
    except ffmpeg.Error as err:
        logger.error(err)
        return None


# ======== create new moderation in DB ========
def create_moderation(moderation_request: CreateModerationRequest):
    try:
        res = MODERATION_DB.insert_one(moderation_request.as_dict())
        if res is None:
            raise ApplicationException(
                "Error while creating moderation", HTTPStatus.INTERNAL_SERVER_ERROR
            )
        return str(res.inserted_id)
    except ApplicationException as err:
        logger.error(err)
        return None


# ======== start the moderation process for the provided moderation ID ========
def start_moderation(object_id: str):
    # Retrieve the ModerationResponse object for the provided ID from the MongoDB database
    moderation = ModerationResponse.from_document(
        MODERATION_DB.find_one({"_id": ObjectId(object_id)})
    )

    # If the moderation cannot be found, raise a 404 exception
    if moderation is None:
        raise ApplicationException("Moderation not found", HTTPStatus.NOT_FOUND)

    # If the moderation is not in the required status, raise a 400 exception
    if moderation.status != str(ModerationStatus.UPLOADED):
        raise ApplicationException(
            "Moderation is not in required status", HTTPStatus.BAD_REQUEST
        )

    # Create an UploadInfo object for the moderation's file
    upload_info = UploadInfo(
        user_id=str(moderation.user_id),
        filename=moderation.filename.split(".")[0],
        file_ext=moderation.filename.split(".")[-1],
        file_with_ext=moderation.filename,
        save_path=os.path.join(
            UPLOAD_PATH, f"{moderation.user_id}_{moderation.filename}"
        ),
    )

    # Set the saved ID of the UploadInfo object to the ID of the moderation in the database
    upload_info.saved_id = str(moderation._id)

    # Create a video metadata list with the duration of the moderation
    video_metadata = [{"duration": moderation.duration}]

    # Enqueue a job to cut the video using the provided UploadInfo and video metadata
    job = redis_conn.enqueue_call(func=cut_video, args=(upload_info, video_metadata))

    # Log the ID of the job and the saved ID of the UploadInfo object for debugging purposes
    logger.info("Job %s started || Cutting Video %s", job.id, upload_info.saved_id)

    # Update the status of the moderation in the database to IN_PROGRESS
    MODERATION_DB.update_one(
        {"_id": ObjectId(object_id)},
        {"$set": {"status": str(ModerationStatus.IN_PROGRESS)}},
    )

    return True


# ======== monthly statistics ========
def get_monthly_statistics(start_date: str, end_date: str) -> Tuple[dict, dict]:
    # Define a MongoDB query pipeline to group all moderations by date and count the number of moderations on each date
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

    # Define a MongoDB query pipeline to group detected moderations by date and count the number of detected moderations on each date
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

    # Execute the all moderation query pipeline and store the results in a list
    all_results = MODERATION_DB.aggregate(all_moderation_query)
    parse_all_results = []
    for result in all_results:
        parse_all_results.append(result)

    # Execute the detected moderation query pipeline and store the results in a list
    detected_results = MODERATION_DB.aggregate(detected_moderation_query)
    parse_detected_results = []
    for result in detected_results:
        parse_detected_results.append(result)

    # Return a tuple containing the parsed results for all moderations and detected moderations
    return parse_all_results, parse_detected_results


# ======== generate a PDF report for the moderation with the provided moderation ID ========
def generate_pdf_report(moderation_id):
    # Retrieve the ModerationResponse object for the provided ID from the MongoDB database
    result = MODERATION_DB.find_one({"_id": ObjectId(moderation_id)})
    moderation = ModerationResponse.from_document(result)

    # Get the HTML template for the PDF report from a Google Cloud Storage bucket
    bucket = GOOGLE_STORAGE_CLIENT.bucket(GOOGLE_BUCKET_NAME)
    html_blob = bucket.blob("template/template_surat_2.html")
    html = html_blob.download_as_text()

    # Generate HTML tags for the moderation's result data
    html_results = generate_html_tags(moderation.result)

    jakarta_time = pytz.timezone("Asia/Jakarta")
    # Replace placeholders in the HTML template with data from the moderation
    html = html.replace(
        "{{current_date}}",
        format_datetime(jakarta_time(datetime.utcnow()), "d MMMM YYYY", locale="id_ID"),
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

    # Generate a PDF file from the HTML template using pdfkit
    pdf = pdfkit.from_string(html, False)

    return pdf


# ======== generate HTML tags for the moderation's result data ========
def validate_moderation(moderation_id, result_index, decision):
    # Retrieve the ModerationResponse object for the provided ID from the MongoDB database
    result = MODERATION_DB.find_one({"_id": ObjectId(moderation_id)})
    moderation = ModerationResponse.from_document(result)
    moderation_result = moderation.result
    moderation_result[int(result_index)]["decision"] = str(
        ModerationDecision.VALID if decision == "VALID" else ModerationDecision.INVALID
    )

    # Update the status of the moderation in the database to the provided decision
    MODERATION_DB.update_one(
        {"_id": ObjectId(moderation_id)}, {"$set": {"result": moderation_result}}
    )

    return True


# ========================================================================
#   utility methods
# ========================================================================


# ======== save the uploaded file to storage, extract metadata, and save moderation information to the database ========
def save_file(upload_info: UploadInfo) -> Tuple[UploadInfo, dict]:
    # Get the video file from the request and the form data containing metadata about the video
    file = request.files["video_file"]
    form_data = request.form

    # Save the video file to the local filesystem and upload it to Google Cloud Storage
    file.save(upload_info.save_path)
    bucket_path = f"uploads/{upload_info.user_id}_{upload_info.file_with_ext}"
    upload_to_gcloud(bucket_path, upload_info.save_path)

    # Read metadata from the uploaded video
    all_metadata = read_video_metadata(upload_info.save_path)
    video_metadata = [data for data in all_metadata if data["codec_type"] == "video"]

    # If the video metadata is None, raise a 400 exception
    if video_metadata is None:
        raise ApplicationException("Video metadata is None", HTTPStatus.BAD_REQUEST)

    # Parse the recording date and start and end times from the form data
    recording_date = datetime.strptime(
        form_data["recording_date"], "%a %b %d %Y %H:%M:%S %Z%z"
    )
    hour, minute, second = recording_date.strftime("%H:%M:%S").split(":")
    start_time = timedelta(hours=int(hour), minutes=int(minute), seconds=int(second))
    end_time = start_time + timedelta(
        seconds=math.floor(float(video_metadata[0]["duration"]))
    )

    frame, divider = video_metadata[0]["r_frame_rate"].split("/")

    # Check for station availability in DB
    tokenized_name = tokenize_string(form_data["station_name"], True)
    query = {"key": tokenized_name}
    station = STATION_DB.find_one(query)
    if station is None:
        [inserted_id, status] = create_station(form_data["station_name"])
        if HTTPStatus.CREATED != status:
            raise ApplicationException(
                "Failed to create station", HTTPStatus.BAD_REQUEST
            )
        station = STATION_DB.find_one({"_id": ObjectId(inserted_id["data"])})

    parsed_station = Station.from_document(station).as_dict()
    parsed_station.pop("created_at")
    parsed_station.pop("updated_at")

    # Create a CreateModerationRequest object with the parsed metadata
    create_request = CreateModerationRequest(
        user_id=upload_info.user_id,
        filename=upload_info.file_with_ext,
        program_name=form_data["program_name"],
        station_name=parsed_station,
        description=form_data["description"],
        recording_date=recording_date,
        start_time=str(start_time),
        end_time=str(end_time),
        fps=round(float(frame) / float(divider), 2),
        duration=round(float(video_metadata[0]["duration"]), 2),
        total_frames=int(video_metadata[0]["nb_frames"]),
    )

    # Create a moderation in the database using the CreateModerationRequest object and get the ID of the new moderation
    object_id = create_moderation(create_request)
    upload_info.saved_id = object_id

    # Return a tuple containing the modified UploadInfo object and the video metadata
    return upload_info, video_metadata


# ======== extract frames from the uploaded video and upload them to Google Cloud Storage ========
def extract_frames(upload_info: UploadInfo, metadata):
    payload = {
        "filename": upload_info.file_with_ext,
        "video_path": f"uploads/{upload_info.user_id}_{upload_info.file_with_ext}",
        "user_id": upload_info.user_id,
    }
    req_response = requests.post(GOOGLE_EXTRACT_FRAME_URL, payload)
    logger.error(str(req_response.json()))
    frame_results = loads(str(req_response.json()).replace("'", '"'))

    # Update the moderation in the database to reference the uploaded frames and set its status to UPLOADED
    MODERATION_DB.update_one(
        {"_id": ObjectId(upload_info.saved_id)},
        {"$set": {"frames": frame_results, "status": str(ModerationStatus.UPLOADED)}},
    )

    logger.info("Frames uploaded to gcloud")


# ! ======== temp ::: cut video and upload to gcs ========
def cut_video(upload_info: UploadInfo, metadata):
    total_duration = float(metadata[0]["duration"])
    timestamp = total_duration / 3

    # check if the file exists in the local directory
    if not os.path.exists(upload_info.save_path):
        # if the file does not exist, download it from GCP bucket
        blob_path = f"uploads/{upload_info.user_id}_{upload_info.file_with_ext}"
        bucket = GOOGLE_STORAGE_CLIENT.bucket(GOOGLE_BUCKET_NAME)
        blob = bucket.blob(blob_path)
        blob.download_to_filename(upload_info.save_path)

    save_path = os.path.join(UPLOAD_PATH, upload_info.filename)
    for i in range(1, 4):
        start_time = max(0, int((timestamp * i) - 2))
        end_time = min(total_duration, int((timestamp * i) + 2))
        ffmpeg_extract_subclip(
            upload_info.save_path,
            start_time,
            end_time,
            targetname=f"{save_path}_{i}.{upload_info.file_ext}",
        )

    temp_videos = []
    videos_to_delete = []
    for i in range(1, 4):
        category = ["SARA", "SARU", "SADIS", "SIHIR", "SIARAN_PARTISAN"]
        category.pop(math.floor(random.random() * len(category)))
        category.pop(math.floor(random.random() * len(category)))
        category.pop(math.floor(random.random() * len(category)))
        save_path = os.path.join(
            UPLOAD_PATH, f"{upload_info.filename}_{i}.{upload_info.file_ext}"
        )
        videos_to_delete.append(save_path)
        bucket_path = f"moderation/{upload_info.user_id}/{upload_info.filename}/videos/{upload_info.user_id}_{upload_info.filename}_{i}.{upload_info.file_ext}"
        temp_videos.append(
            {
                "second": timestamp * i,
                "clip_url": bucket_path,
                "decision": str(ModerationDecision.PENDING),
                "category": category,
            }
        )
        upload_to_gcloud(bucket_path, save_path)

    for video in videos_to_delete:
        os.remove(video)

    MODERATION_DB.update_one(
        {"_id": ObjectId(upload_info.saved_id)},
        {"$set": {"result": temp_videos, "status": str(ModerationStatus.REJECTED)}},
    )

    logger.info("Videos uploaded to gcloud")


# ======== main method to upload to gcs ========
def upload_to_gcloud(destination, source):
    try:
        bucket = GOOGLE_STORAGE_CLIENT.bucket(GOOGLE_BUCKET_NAME)
        user_blob = bucket.blob(destination)
        user_blob.upload_from_filename(source)
        user_blob.make_public()
    except (TimeoutError, ApplicationException) as err:
        logger.error(err)


# ======== generate HTML tags to display the moderation result in a PDF report ========
def generate_html_tags(result):
    html_tags = ""
    count = 1
    for _, val in enumerate(result):
        # If the decision is not "valid", skip this result
        if str(val["decision"]).upper() != "VALID":
            continue

        # Create a comma-separated string of categories
        categories = ""
        for category in val["category"]:
            category = str(category).replace("_", " ")
            categories += f"{category}" if categories == "" else f", {category}"

        # Add an <li> element containing a link to the video and the detected categories to the HTML string
        html_tags += f"""
        <li>
            <a href="https://{GOOGLE_BUCKET_NAME}.storage.googleapis.com/{val["clip_url"]}">Video {count}</a>
            <br/>
            Terdeteksi mengandung unsur melanggar {categories}
        </li>
        """
        count += 1
    return html_tags
