import logging
import math
import os
from dataclasses import asdict

import ffmpeg
from bson.objectid import ObjectId
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.video.io.VideoFileClip import VideoFileClip

from app.dto import CreateModerationRequest, UploadInfo
from config import STORAGE_CLIENT, UPLOAD_PATH, database

# ======== INITIALIZATIONS ========
logger = logging.getLogger(__name__)
MODERATION_DB = database["moderation"]


# ======== READ VIDEO METADATA ========
def read_video_metadata(file_path):
    try:
        metadata = ffmpeg.probe(file_path)["streams"]
        return metadata
    except Exception as e:
        logger.error(e)
        return None


# ======== CREATE NEW OBJECT IN DB ========
def create_moderation(moderation_request: CreateModerationRequest):
    try:
        res = MODERATION_DB.insert_one(asdict(moderation_request))
        return str(res.inserted_id)
    except Exception as e:
        logger.error(e)
        return None


# ======== EXTRACT FRAMES AND UPLOAD ========
def extract_frames(upload_info: UploadInfo, metadata):
    clip = VideoFileClip(upload_info.save_path)

    for i in range(0, math.floor(float(metadata[0]["duration"]))):
        save_path = f'{UPLOAD_PATH}/{upload_info.filename}_f{i}.jpg'
        logger.info(f"Saving frame {i} to {save_path}")
        clip.save_frame(save_path, i)

    temp_frames = []
    for i in range(0, math.floor(float(metadata[0]["duration"]))):
        save_path = f'{UPLOAD_PATH}/{upload_info.filename}_f{i}.jpg'
        bucket_path = f"moderation/{upload_info.user_id}/{upload_info.filename}/frames/{upload_info.user_id}_{upload_info.filename}_f{i}.jpg"
        temp_frames.append(bucket_path)
        upload_to_gcloud(bucket_path, save_path)

    MODERATION_DB.update_one({"_id": ObjectId(upload_info.saved_id)}, {"$set": {
                             "frames": temp_frames}})


# ! ======== TEMP ::: CUT VIDEO AND UPLOAD TO GCS ========
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
    for i in range(1, 4):
        save_path = os.path.join(
            UPLOAD_PATH, f"{upload_info.filename}_{i}.{upload_info.file_ext}")
        bucket_path = f"moderation/{upload_info.user_id}/{upload_info.filename}/videos/{upload_info.user_id}_{upload_info.filename}_{i}.{upload_info.file_ext}"
        temp_videos.append(bucket_path)
        upload_to_gcloud(bucket_path, save_path)

    MODERATION_DB.update_one({"_id": ObjectId(upload_info.saved_id)}, {"$set": {
                             "videos": temp_videos}})


# ======== MAIN METHOD TO UPLOAD TO GCS ========
def upload_to_gcloud(destination, source):
    try:
        bucket = STORAGE_CLIENT.bucket("kpid-jatim")
        user_blob = bucket.blob(destination)
        user_blob.upload_from_filename(source)
        user_blob.make_public()
    except Exception as e:
        logger.error(e)

