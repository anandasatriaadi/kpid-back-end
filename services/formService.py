from http import HTTPStatus
import logging
from flask import request
from controllers.utils import token_required
import os

import math
from config import database
from response.BaseResponse import BaseResponse
from utils.CustomFormatter import init_logging
from response.form.FormResponse import FormResponse
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.video.io.VideoFileClip import VideoFileClip
import ffmpeg

from google.oauth2 import service_account
from google.cloud import storage

# ======== INITIALIZATIONS ========
init_logging()
logger = logging.getLogger(__name__)
storage_client = storage.Client.from_service_account_json(
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

# ======== POST : login user ========
@token_required
def upload_form(current_user):
    response = BaseResponse()
    moderation = database["moderation"]
    FILE = request.files['video_file']
    FORM_DATA = request.form

    # Save video to storage
    user_id = str(current_user["_id"])
    filename = f"{user_id}_{FILE.filename}"
    save_path = os.path.join(f'{os.getcwd()}/uploads', filename)
    FILE.save(save_path)

    # Process uploaded video
    all_metadata = read_video_metadata(save_path)
    video_metadata = [
        data for data in all_metadata if data["codec_type"] == "video"]

    # Extract frames from video
    if video_metadata is None:
        raise Exception("Video metadata is None")
    else:
        __extract_frames(user_id, save_path, filename, video_metadata)
        __cut_video(user_id, save_path, filename, video_metadata)

    form_response = FormResponse(program_name=FORM_DATA["program_name"], filename=filename, station_name=FORM_DATA["station_name"],
                                 start_time=FORM_DATA["start_time"], frame_rate=video_metadata[0]["r_frame_rate"], duration=video_metadata[0]["duration"])
    response.set_response(video_metadata, HTTPStatus.OK)
    return response.__dict__, response.status

# ======== READ VIDEO METADATA ========
def read_video_metadata(file_path):
    try:
        metadata = ffmpeg.probe(file_path)["streams"]
        return metadata
    except Exception as e:
        logger.error(e)
        return None


def __extract_frames(user_id, file_path, filename, metadata):
    filenames = filename.split(".")
    clip = VideoFileClip(file_path)

    for i in range(0, math.floor(float(metadata[0]["duration"])) * 2):
        save_path = f'{os.getcwd()}/uploads/{filenames[0]}_f{i}.jpg'
        logger.info(f"Saving frame {i} to {save_path}")
        clip.save_frame(save_path, i / 2)
        __upload_frame(save_path, user_id, f"{filenames[0]}_f{i}.jpg")

    return True


def __cut_video(user_id, file_path, filename, metadata):
    milisecond_per_frame = int(
        1000/int(metadata[0]["r_frame_rate"].split("/")[0]))
    timestamp = float(metadata[0]["duration"])/3
    filenames = filename.split(".")
    for i in range(1, 4):
        save_path = os.path.join(f'{os.getcwd()}/uploads', filenames[0])
        start_time = int((timestamp*i) - 2)
        end_time = 0
        if i == 3:
            end_time = int(timestamp*i)
        else:
            end_time = int((timestamp*i) + 2)
        print(f"Start time: {start_time}")
        print(f"End time: {end_time}")
        print(f"Saving to {save_path}_{i}.{filenames[1]}")
        ffmpeg_extract_subclip(
            file_path, start_time, end_time, targetname=f"{save_path}_{i}.{filenames[1]}")

    for i in range(1, 4):
        save_path = os.path.join(f'{os.getcwd()}/uploads', filenames[0])
        __upload_video(
            f"{save_path}_{i}.{filenames[1]}", filenames[0], f"{i}.{filenames[1]}")
    return True


def __upload_to_gcloud(destination, source):
    try:
        bucket = storage_client.bucket("kpid-jatim")
        user_blob = bucket.blob(destination)
        user_blob.upload_from_filename(source)
        user_blob.make_public()
    except Exception as e:
        logger.error(e)
        return False


def __upload_frame(file_to_upload, user_id, filename):
    return __upload_to_gcloud(f"moderation/{user_id}/frames/{filename}", file_to_upload)


def __upload_video(file_to_upload, user_id, filename):
    return __upload_to_gcloud(f"moderation/{user_id}/videos/{filename}", file_to_upload)
