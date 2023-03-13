import os
from datetime import datetime, timedelta
from http import HTTPStatus

from flask import Blueprint, request

from app.api.common.utils import token_required
from app.api.moderation.moderation_service import (create_moderation,
                                                   cut_video, extract_frames,
                                                   read_video_metadata)
from app.dto import BaseResponse, CreateModerationRequest, UploadInfo
from config import UPLOAD_PATH

moderation_bp = Blueprint('moderation', __name__)


# ======== POST : UPLOAD MODERATION FORM ========
@moderation_bp.route('/moderation-form', methods=['POST'])
@token_required
def upload_form(current_user):
    response = BaseResponse()
    file = request.files['video_file']
    form_data = request.form
    upload_info = UploadInfo(
        user_id=str(current_user["user_id"]),
        filename=f"{file.filename.split('.')[0]}",
        file_ext=f"{file.filename.split('.')[-1]}",
        file_with_ext=f"{file.filename}",
        save_path=os.path.join(
            UPLOAD_PATH, f"{str(current_user['user_id'])}_{file.filename}"),
    )

    # Save video to storage
    file.save(upload_info.save_path)

    # Process uploaded video
    all_metadata = read_video_metadata(upload_info.save_path)
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
    object_id = create_moderation(create_request)
    upload_info.saved_id = object_id

    # Extract frames from video
    if video_metadata is None:
        raise Exception("Video metadata is None")
    else:
        extract_frames(upload_info, video_metadata)
        cut_video(upload_info, video_metadata)

    response.set_response("i", HTTPStatus.OK)
    return response.get_response()
