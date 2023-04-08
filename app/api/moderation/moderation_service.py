import logging
import math
import os
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Tuple

import ffmpeg
from bson.objectid import ObjectId
from flask import request
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.video.io.VideoFileClip import VideoFileClip

from app.api.common.utils import clean_query_params, parse_query_params
from app.api.exceptions import ApplicationException
from app.dto import (CreateModerationRequest, ModerationResponse,
                     PaginateResponse, UploadInfo, ModerationStatus)
from config import STORAGE_CLIENT, UPLOAD_PATH, database

# ======== INITIALIZATIONS ========
logger = logging.getLogger(__name__)
MODERATION_DB = database["moderation"]


# ======== get moderation data by params ========
def get_by_params(query_params: dict) -> PaginateResponse:
    response = PaginateResponse()
    moderation = database["moderation"]

    params, pagination = clean_query_params(query_params)
    query, sort = parse_query_params(params)
    logger.info(query)
    logger.info(sort)

    output = []
    total_elements = moderation.count_documents(query)

    results = None
    if len(sort) > 0:
        if len(pagination) > 0:
            results = moderation.find(query).sort(sort).skip(
                pagination["limit"] * pagination["page"]).limit(pagination["limit"])
        else:
            results = moderation.find(query).sort(sort)
    else:
        if len(pagination) > 0:
            results = moderation.find(query).skip(
                pagination["limit"] * pagination["page"]).limit(pagination["limit"])
        else:
            results = moderation.find(query)

    for result in results:
        output.append(ModerationResponse.from_document(result))

    if len(pagination) > 0:
        response.set_metadata(pagination["page"], pagination["limit"], total_elements, math.ceil(
            total_elements/pagination["limit"]))
    response.set_response(output, HTTPStatus.OK)

    return response


# ======== get count by params ========
def get_count_by_params(query_params: dict) -> int:
    moderation = database["moderation"]

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


# ======== Create New Object In DB ========
def create_moderation(moderation_request: CreateModerationRequest):
    try:
        res = MODERATION_DB.insert_one(moderation_request.as_dict())
        if res is None:
            raise ApplicationException(
                "Error while creating moderation", HTTPStatus.INTERNAL_SERVER_ERROR)
        return str(res.inserted_id)
    except ApplicationException as err:
        logger.error(err)
        return None


# ========================================================================
#   utility methods
# ========================================================================


# ======== save file into local and data into db and return video metadata ========
def save_file(upload_info: UploadInfo) -> Tuple[UploadInfo, dict]:
    # Save video to storage
    file = request.files['video_file']
    form_data = request.form

    file.save(upload_info.save_path)

    # Process uploaded video
    all_metadata = read_video_metadata(upload_info.save_path)
    video_metadata = [
        data for data in all_metadata if data["codec_type"] == "video"]

    # Extract frames from video
    if video_metadata is None:
        raise ApplicationException(
            "Video metadata is None", HTTPStatus.BAD_REQUEST
        )

    # Save moderation information to database
    hour, minute, second = datetime.strptime(
        form_data["start_time"], '%a %b %d %Y %H:%M:%S %Z%z').strftime('%H:%M:%S').split(':')
    start_time = timedelta(
        hours=int(hour), minutes=int(minute), seconds=int(second)
    )
    end_time = start_time + \
        timedelta(seconds=math.floor(float(video_metadata[0]["duration"])))

    frame, divider = video_metadata[0]["r_frame_rate"].split("/")

    create_request = CreateModerationRequest(
        user_id=upload_info.user_id,
        filename=upload_info.file_with_ext,
        program_name=form_data["program_name"],
        station_name=form_data["station_name"],
        description=form_data["description"],
        start_time=str(start_time),
        end_time=str(end_time),
        fps=round(float(frame)/float(divider), 2),
        duration=round(float(video_metadata[0]["duration"]), 2),
        total_frames=int(video_metadata[0]["nb_frames"])
    )
    object_id = create_moderation(create_request)
    upload_info.saved_id = object_id

    return upload_info, video_metadata


# ======== extract frames and upload ========
def extract_frames(upload_info: UploadInfo, metadata):
    clip = VideoFileClip(upload_info.save_path)

    for i in range(0, math.floor(float(metadata[0]["duration"]))):
        save_path = f'{UPLOAD_PATH}/{upload_info.filename}_f{i}.jpg'
        logger.info("Saving frame %s to %s", i, save_path)
        clip.save_frame(save_path, i)

    temp_frames = []
    frames_to_delete = []
    for i in range(0, math.floor(float(metadata[0]["duration"]))):
        save_path = f'{UPLOAD_PATH}/{upload_info.filename}_f{i}.jpg'
        frames_to_delete.append(save_path)
        bucket_path = f"moderation/{upload_info.user_id}/{upload_info.filename}/frames/{upload_info.user_id}_{upload_info.filename}_f{i}.jpg"
        temp_frames.append(bucket_path)
        upload_to_gcloud(bucket_path, save_path)

    for frame in frames_to_delete:
        os.remove(frame)

    MODERATION_DB.update_one({"_id": ObjectId(upload_info.saved_id)}, {"$set": {
                             "frames": temp_frames, "status": ModerationStatus.UPLOADED.__str__()}})


# ! ======== temp ::: cut video and upload to gcs ========
def cut_video(upload_info: UploadInfo, metadata):
    milisecond_per_frame = int(
        1000/int(metadata[0]["r_frame_rate"].split("/")[0]))
    timestamp = float(metadata[0]["duration"])/3
    for i in range(1, 4):
        save_path = os.path.join(UPLOAD_PATH, upload_info.filename)
        start_time = int((timestamp*i) - 2)
        end_time = 0
        if i == 3:
            end_time = int(timestamp*i)
        else:
            end_time = int((timestamp*i) + 2)
        ffmpeg_extract_subclip(
            upload_info.save_path, start_time, end_time, targetname=f"{save_path}_{i}.{upload_info.file_ext}")

    temp_videos = []
    videos_to_delete = []
    for i in range(1, 4):
        save_path = os.path.join(
            UPLOAD_PATH, f"{upload_info.filename}_{i}.{upload_info.file_ext}")
        videos_to_delete.append(save_path)
        bucket_path = f"moderation/{upload_info.user_id}/{upload_info.filename}/videos/{upload_info.user_id}_{upload_info.filename}_{i}.{upload_info.file_ext}"
        temp_videos.append(bucket_path)
        upload_to_gcloud(bucket_path, save_path)

    for video in videos_to_delete:
        os.remove(video)

    MODERATION_DB.update_one({"_id": ObjectId(upload_info.saved_id)}, {"$set": {
                             "videos": temp_videos}})


# ======== main method to upload to gcs ========
def upload_to_gcloud(destination, source):
    try:
        bucket = STORAGE_CLIENT.bucket("kpid-jatim")
        user_blob = bucket.blob(destination)
        user_blob.upload_from_filename(source)
        user_blob.make_public()
    except (TimeoutError, ApplicationException) as err:
        logger.error(err)

