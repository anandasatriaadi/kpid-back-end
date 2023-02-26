from http import HTTPStatus
import logging
from flask import request
from controllers.utils import token_required
import os

from config import database
from response.BaseResponse import BaseResponse
from utils.CustomFormatter import init_logging
from response.form.FormResponse import FormResponse
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
import ffmpeg

init_logging()
logger = logging.getLogger(__name__)

# ======== POST : login user ========
@token_required
def upload_form(current_user):
    response = BaseResponse()
    moderation = database["moderation"]
    file = request.files['']
    user_id = str(current_user["_id"])
    filename = f"{user_id}_{file.filename}"
    save_path = os.path.join(f'{os.getcwd()}/uploads', filename)
    file.save(save_path)

    all_metadata = read_video_metadata(save_path)
    video_metadata = [
        data for data in all_metadata if data["codec_type"] == "video"]

    if video_metadata is None:
        raise Exception("Video metadata is None")
    else:
        cut_video(save_path, filename, video_metadata)

    form_response = FormResponse(program_name=request.form["program_name"], filename=filename, station_name=request.form["station_name"],
                                 start_time=request.form["start_time"], frame_rate=video_metadata[0]["r_frame_rate"], duration=video_metadata[0]["duration"])
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


def cut_video(file_path, filename, metadata):
    milisecond_per_frame = int(
        1000/int(metadata[0]["r_frame_rate"].split("/")[0]))
    timestamp = float(metadata[0]["duration"])/3
    for i in range(1, 4):
        filenames = filename.split(".")
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
    return True
