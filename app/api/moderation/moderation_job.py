import logging
import math
import os
from datetime import datetime, timedelta
from http import HTTPStatus
from json import loads
from typing import Tuple

import ffmpeg
import requests
from bson.objectid import ObjectId
from flask import request
from moviepy.editor import VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_audio, ffmpeg_extract_subclip
from rq import Queue

from ai_utils.detect import detect_objects
from ai_utils.extract import keyframe_detection
from app.api.common.gcloud_utils import (
    delete_file_gcloud,
    download_files_gcloud,
    upload_to_gcloud,
)
from app.api.common.string_utils import tokenize_string
from app.api.exceptions import ApplicationException
from app.api.station.station_service import create_station
from app.dto import (
    CreateModerationRequest,
    Moderation,
    ModerationStatus,
    Station,
    UploadInfo,
)
from config import (
    DATABASE,
    GOOGLE_BUCKET_NAME,
    GOOGLE_EXTRACT_FRAME_URL,
    GOOGLE_STORAGE_CLIENT,
    UPLOAD_PATH,
    USE_GOOGLE_FUNCTIONS,
)
from redis_worker import conn

redis_conn = Queue(connection=conn)
logger = logging.getLogger(__name__)
MODERATION_DB = DATABASE["moderation"]
STATION_DB = DATABASE["stations"]


# Read Video Metadata
def extract_metadata(upload_info: UploadInfo) -> dict:
    try:
        metadata = ffmpeg.probe(upload_info.video_save_path)["streams"]
        video_metadata = [data for data in metadata if data["codec_type"] == "video"]
        return video_metadata
    except ffmpeg.Error as err:
        logger.error(err)
        return None


def convert_video_extract_audio(upload_info: UploadInfo) -> bool:
    try:
        # Convert Video Format to mp4 if necessary
        if not upload_info.file_ext.lower() == "mp4":
            logger.info("Converting video to mp4")
            mp4_save_path = upload_info.filename + ".mp4"
            video_clip = VideoFileClip(upload_info.video_save_path)
            video_clip.write_videofile(mp4_save_path, codec="libx264")
            video_clip.close()

            # Remove the original video file
            os.remove(upload_info.video_save_path)

            # Update the upload_info with the new video save path
            upload_info.video_save_path = mp4_save_path

        ffmpeg_extract_audio(upload_info.video_save_path, f"{UPLOAD_PATH}/{upload_info.filename}.mp3")
        upload_info.audio_save_path = f"{UPLOAD_PATH}/{upload_info.filename}.mp3"
        return True
    except ffmpeg.Error as err:
        logger.error(err)
        return False

def convert_and_upload_to_gcloud(upload_info):
    convert_video_extract_audio(upload_info)

    # Upload The Video and Audio To Google Cloud Storage
    vid_bucket_path = f"uploads/{upload_info.user_id}_{upload_info.file_with_ext}"
    upload_to_gcloud(vid_bucket_path, upload_info.video_save_path)

    aud_bucket_path = f"uploads/{upload_info.user_id}_{upload_info.filename}.mp3"
    upload_to_gcloud(aud_bucket_path, upload_info.audio_save_path)

    # Delete The Local Video And Audio Files
    os.remove(upload_info.video_save_path)
    os.remove(upload_info.audio_save_path)


# Create New Moderation In DB
def create_moderation(moderation_request: CreateModerationRequest) -> str:
    try:
        res = MODERATION_DB.insert_one(moderation_request.as_dict())
        if res is None:
            raise ApplicationException(
                "Error while creating moderation", HTTPStatus.INTERNAL_SERVER_ERROR
            )
        return str(res.inserted_id)
    except Exception as err:
        logger.error(err)
        raise(err)


# Save The Uploaded File To Storage, Extract Metadata, And Save Moderation Information To The Database
def save_file(upload_info: UploadInfo) -> Tuple[UploadInfo, dict]:
    # Get The Video File From The Request And The Form Data Containing Metadata About The Video
    file = request.files["video_file"]
    form_data = request.form

    # Save Video And Extract The Metedata And Audio
    file.save(upload_info.video_save_path)
    video_metadata = extract_metadata(upload_info)

    job = redis_conn.enqueue_call(
            func=convert_and_upload_to_gcloud, args=([upload_info])
        )
    logger.info(
        "Job %s queued || Convert Video and Extract Audio  %s", job.id, upload_info.filename
    )

    # If The Video Metadata Is None, Raise A 400 Exception
    if video_metadata is None:
        raise ApplicationException("Video metadata is None", HTTPStatus.BAD_REQUEST)

    # Parse The Recording Date And Start And End Times From The Form Data
    recording_date = datetime.strptime(
        form_data["recording_date"], "%a %b %d %Y %H:%M:%S %Z%z"
    )
    hour, minute, second = recording_date.strftime("%H:%M:%S").split(":")
    start_time = timedelta(hours=int(hour), minutes=int(minute), seconds=int(second))
    end_time = start_time + timedelta(
        seconds=math.floor(float(video_metadata[0]["duration"]))
    )

    frame, divider = video_metadata[0]["r_frame_rate"].split("/")

    # Check For Station Availability In Db
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

    # Create A Createmoderationrequest Object With The Parsed Metadata
    create_request = CreateModerationRequest(
        user_id=upload_info.user_id,
        filename=f"{upload_info.filename}.mp4",
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

    # Create A Moderation In The Database Using The Createmoderationrequest Object And Get The ID Of The New Moderation
    object_id = create_moderation(create_request)
    upload_info.saved_id = object_id

    # Return A Tuple Containing The Modified Uploadinfo Object And The Video Metadata
    return upload_info, video_metadata


# Extract Frames From The Uploaded Video And Upload Them To Google Cloud Storage
def extract_frames(upload_info: UploadInfo, metadata):
    try:
        video_path = f"uploads/{upload_info.user_id}_{upload_info.file_with_ext}"
        payload = {
            "filename": upload_info.file_with_ext,
            "video_path": video_path,
            "user_id": upload_info.user_id,
        }

        logger.error(USE_GOOGLE_FUNCTIONS)
        if USE_GOOGLE_FUNCTIONS:
            req_response = requests.post(GOOGLE_EXTRACT_FRAME_URL, payload)
            logger.error(str(req_response.json()))
            frame_results = loads(str(req_response.json()).replace("'", '"'))
        else:
            bucket = GOOGLE_STORAGE_CLIENT.bucket(GOOGLE_BUCKET_NAME)
            source_blob = bucket.get_blob(video_path)
            frame_results = keyframe_detection(
                upload_info.user_id, upload_info.file_with_ext, source_blob, bucket, 0.4
            )

        # Update The Moderation In The Database To Reference The Uploaded Frames And Set Its Status To Uploaded
        MODERATION_DB.update_one(
            {"_id": ObjectId(upload_info.saved_id)},
            {
                "$set": {
                    "frames": frame_results,
                    "status": str(ModerationStatus.UPLOADED),
                }
            },
        )

        logger.info("Frames uploaded to gcloud")
    except Exception as e:
        logger.error(e)
        MODERATION_DB.delete_one({"_id": ObjectId(upload_info.saved_id)})


def moderate_video(upload_info: UploadInfo, metadata):
    initial_data = MODERATION_DB.find_one({"_id": ObjectId(upload_info.saved_id)})
    try:
        # Update The Status Of The Moderation In The Database To In_Progress
        MODERATION_DB.update_one(
            {"_id": ObjectId(upload_info.saved_id)},
            {"$set": {"status": str(ModerationStatus.IN_PROGRESS)}},
        )

        total_duration = float(metadata[0]["duration"])

        # Download All Frame Files Before Detecting The Frames Using Model
        moderation_data = Moderation.from_document(initial_data)
        frame_urls = [item["frame_url"] for item in moderation_data.frames]
        download_files_gcloud(UPLOAD_PATH, frame_urls)

        # Detect The Frames Using Model
        detected_frames = detect_objects(moderation_data.frames)

        # Check If The Video File Exists And Download If Not Exists
        if not os.path.exists(upload_info.video_save_path):
            blob_path = f"uploads/{upload_info.user_id}_{upload_info.file_with_ext}"
            download_files_gcloud(UPLOAD_PATH, [blob_path])

        # Clip The Video File Based On The Detected Frames
        videos_to_delete = []
        clipped_video_save_path = os.path.join(UPLOAD_PATH, upload_info.filename)
        for idx, detected in enumerate(detected_frames):
            start_time = max(0, float(detected.second - 2.5))
            end_time = min(total_duration, float(detected.second + 2.5))
            ffmpeg_extract_subclip(
                upload_info.video_save_path,
                start_time,
                end_time,
                targetname=f"{clipped_video_save_path}_{idx}.{upload_info.file_ext}",
            )

        # Upload The Clipped Video Files To Google Cloud Storage
        for idx, detected in enumerate(detected_frames):
            videos_to_delete.append(
                f"{clipped_video_save_path}_{idx}.{upload_info.file_ext}"
            )
            bucket_path = f"moderation/{upload_info.user_id}/{upload_info.filename}/videos/{upload_info.user_id}_{upload_info.filename}_{idx}.{upload_info.file_ext}"
            detected.clip_url = bucket_path
            upload_to_gcloud(
                bucket_path, f"{clipped_video_save_path}_{idx}.{upload_info.file_ext}"
            )

        # Convert From Frameresult Object To Dict
        parsed_result = [item.as_dict() for item in detected_frames]

        # Delete Local Images And Videos
        for frame in moderation_data.frames:
            os.remove(f"{UPLOAD_PATH}/{frame['frame_url'].split('/')[-1]}")
        for video in videos_to_delete:
            os.remove(video)

        # Update Moderation Data
        MODERATION_DB.update_one(
            {"_id": ObjectId(upload_info.saved_id)},
            {
                "$set": {
                    "result": parsed_result,
                    "status": str(ModerationStatus.REJECTED),
                }
            },
        )

        # Delete The Uploaded Video File From Google Cloud Storage
        delete_file_gcloud(f"uploads/{upload_info.user_id}_{upload_info.file_with_ext}")

        logger.info("Videos uploaded to gcloud")
    except Exception as e:
        logger.error(e)
        MODERATION_DB.update_one(
            {"_id": ObjectId(upload_info.saved_id)},
            {"$set": initial_data},
        )


# Generate HTML Tags To Display The Moderation Result In A PDF Report
def generate_html_tags(result):
    html_tags = ""
    count = 1
    for _, val in enumerate(result):
        # If The Decision Is Not "VALID", Skip This Result
        if str(val["decision"]).upper() != "VALID":
            continue

        # Create A Comma-Separated String Of Categories
        categories = ""
        for category in val["category"]:
            category = str(category).upper().replace("_", " ")
            categories += f"{category}" if categories == "" else f", {category}"

        # Add An <li> Element Containing A Link To The Video And The Detected Categories To The HTML String
        html_tags += f"""
        <li style="margin-bottom: 0.25rem">
            <a target="_blank" href="https://{GOOGLE_BUCKET_NAME}.storage.googleapis.com/{val["clip_url"]}">Video {count}</a>
            <br/>
            Terdeteksi mengandung unsur melanggar {categories}
        </li>
        """
        count += 1
    return html_tags
