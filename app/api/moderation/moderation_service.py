import logging
import math
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from http import HTTPStatus

import ffmpeg
from bson.objectid import ObjectId
from dacite import from_dict
from flask import request
from google.cloud import storage
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.video.io.VideoFileClip import VideoFileClip

from app.api.common.utils import token_required
from app.dto import CreateModerationRequest, BaseResponse, ModerationResponse
from config import database

# ======== INITIALIZATIONS ========
logger = logging.getLogger(__name__)
MODERATION_DB = database["moderation"]
STORAGE_CLIENT = storage.Client.from_service_account_json(
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
UPLOAD_PATH = f"{os.getcwd()}/uploads"


@dataclass
class UploadInfo(object):
    user_id: str
    filename: str
    file_ext: str
    file_with_ext: str
    save_path: str
    saved_id: str = field(init=False)

# ======== POST : UPLOAD MODERATION FORM ========


@token_required
def upload_form(current_user):
    response = BaseResponse()
    file = request.files['video_file']
    form_data = request.form
    upload_info = UploadInfo(
        user_id=str(current_user["_id"]),
        filename=f"{file.filename.split('.')[0]}",
        file_ext=f"{file.filename.split('.')[-1]}",
        file_with_ext=f"{file.filename}",
        save_path=os.path.join(
            UPLOAD_PATH, f"{str(current_user['_id'])}_{file.filename}"),
    )

    # Save video to storage
    file.save(upload_info.save_path)

    # Process uploaded video
    all_metadata = __read_video_metadata(upload_info.save_path)
    video_metadata = [
        data for data in all_metadata if data["codec_type"] == "video"]

    # Save moderation information to database
    hour, min, sec = datetime.strptime(
        form_data["start_time"], '%a %b %d %Y %H:%M:%S %Z%z').strftime('%H:%M:%S').split(':')
    start_time = timedelta(
        hours=int(hour), minutes=int(min), seconds=int(sec)
    )
    end_time = start_time + \
        timedelta(seconds=float(video_metadata[0]["duration"]))

    create_request = CreateModerationRequest(
        user_id=upload_info.user_id,
        filename=upload_info.file_with_ext,
        program_name=form_data["program_name"],
        station_name=form_data["station_name"],
        start_time=str(start_time),
        end_time=str(end_time),
        fps=int(video_metadata[0]["r_frame_rate"].split("/")[0]),
        duration=float(video_metadata[0]["duration"]),
        total_frames=int(video_metadata[0]["nb_frames"])
    )
    object_id = __create_moderation(create_request)
    upload_info.saved_id = object_id

    # Extract frames from video
    if video_metadata is None:
        raise Exception("Video metadata is None")
    else:
        __extract_frames(upload_info, video_metadata)
        __cut_video(upload_info, video_metadata)

    response.set_response("i", HTTPStatus.OK)
    return response.__dict__, response.status


# ======== READ VIDEO METADATA ========
def __read_video_metadata(file_path):
    try:
        metadata = ffmpeg.probe(file_path)["streams"]
        return metadata
    except Exception as e:
        logger.error(e)
        return None


# ======== CREATE NEW OBJECT IN DB ========
def __create_moderation(moderation_request: CreateModerationRequest):
    try:
        res = MODERATION_DB.insert_one(asdict(moderation_request))
        return str(res.inserted_id)
    except Exception as e:
        logger.error(e)
        return None


# ======== EXTRACT FRAMES AND UPLOAD ========
def __extract_frames(upload_info: UploadInfo, metadata):
    clip = VideoFileClip(upload_info.save_path)

    for i in range(0, math.floor(float(metadata[0]["duration"]))):
        save_path = f'{UPLOAD_PATH}/{upload_info.filename}_f{i}.jpg'
        logger.info(f"Saving frame {i} to {save_path}")
        clip.save_frame(save_path, i)

    temp_frames = []
    for i in range(0, math.floor(float(metadata[0]["duration"]))):
        save_path = f'{UPLOAD_PATH}/{upload_info.filename}_f{i}.jpg'
        __upload_frame(save_path, upload_info.user_id,
                       f"{upload_info.filename}_f{i}.jpg")
        temp_frames.append(
            f"moderation/{upload_info.user_id}/frames/{upload_info.filename}_f{i}.jpg")
    MODERATION_DB.update_one({"_id": ObjectId(upload_info.saved_id)}, {"$set": {
                             "frames": temp_frames}})


# ! ======== TEMP ::: CUT VIDEO AND UPLOAD TO GCS ========
def __cut_video(upload_info: UploadInfo, metadata):
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
    for i in range(1, 4):
        save_path = os.path.join(
            UPLOAD_PATH, f"{upload_info.filename}_{i}.{upload_info.file_ext}")
        temp_videos.append(
            f"moderation/{upload_info.user_id}/videos/{upload_info.filename}_{i}.{upload_info.file_ext}")
        __upload_video(
            save_path, upload_info.user_id, f"{upload_info.filename}_{i}.{upload_info.file_ext}")

    MODERATION_DB.update_one({"_id": ObjectId(upload_info.saved_id)}, {"$set": {
                             "videos": temp_videos}})


# ======== MAIN METHOD TO UPLOAD TO GCS ========
def __upload_to_gcloud(destination, source):
    try:
        bucket = STORAGE_CLIENT.bucket("kpid-jatim")
        user_blob = bucket.blob(destination)
        user_blob.upload_from_filename(source)
        user_blob.make_public()
    except Exception as e:
        logger.error(e)


def __upload_frame(file_to_upload, user_id, filename):
    return __upload_to_gcloud(f"moderation/{user_id}/frames/{filename}", file_to_upload)


def __upload_video(file_to_upload, user_id, filename):
    return __upload_to_gcloud(f"moderation/{user_id}/videos/{filename}", file_to_upload)
