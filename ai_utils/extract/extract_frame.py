import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

import cv2

# ONLY ENABLE WHEN ON GOOGLE CLOUD FUNCTIONS
# import functions_framework
import numpy as np
import peakutils
from flask import Request, make_response
from google.cloud import storage
from PIL import Image


def __scale(img, x_scale, y_scale):
    """Resize the input image using the provided scaling factors."""
    return cv2.resize(img, None, fx=x_scale, fy=y_scale, interpolation=cv2.INTER_AREA)


def __crop(infile, height, width):
    """Yield cropped images from the input file based on the provided height and width."""
    im = Image.open(infile)
    img_width, img_height = im.size
    for i in range(img_height // height):
        for j in range(img_width // width):
            box = (j * width, i * height, (j + 1) * width, (i + 1) * height)
            yield im.crop(box)


def __average_pixels(path):
    """Compute the average RGB values of the input image."""
    r, g, b = 0, 0, 0
    count = 0
    pic = Image.open(path)
    for x in range(pic.size[0]):
        for y in range(pic.size[1]):
            img_data = pic.load()
            temp_r, temp_g, temp_b = img_data[x, y]
            r += temp_r
            g += temp_g
            b += temp_b
            count += 1
    return (r / count), (g / count), (b / count), count


def __convert_frame_to_grayscale(frame):
    """Convert the input frame to grayscale and apply Gaussian blur."""
    gray_frame = None
    gray = None
    if frame is not None:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_frame = gray.copy()
        gray = cv2.GaussianBlur(gray, (9, 9), 0.0)
    return gray_frame, gray


def keyframe_detection(user_id, filename, source, dest, threshold, plot_metrics=False, verbose=False):
    """Detect keyframes in the input video and upload them to the destination bucket."""
    filename = Path(str(filename))
    print(filename)
    filename_wo_ext = filename.with_suffix('')

    folder_path = f"moderation/{user_id}/{filename_wo_ext}/frames"

    video_path = None
    if(Path.cwd().joinpath("uploads", f"{user_id}_{filename}").exists()):
        print("File Exists")
        video_path = Path.cwd().joinpath("uploads", f"{user_id}_{filename}")
    else:
        source.download_to_filename('/tmp/video.mp4')
        video_path = '/tmp/video.mp4'
    cap = cv2.VideoCapture(str(video_path))
    length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    if not cap.isOpened():
        print("Error opening video file")
        return []

    list_diff_mag = []
    time_spans = []
    images = []
    full_color = []
    last_frame = None

    print(f"length {length}")
    print(f"fps {fps}")
    curr_iter = 0
    while (curr_iter * fps) <= length:
        cap.set(cv2.CAP_PROP_POS_FRAMES, curr_iter * fps)
        _, frame = cap.read()

        gray_frame, blur_gray = __convert_frame_to_grayscale(frame)

        frame_number = cap.get(cv2.CAP_PROP_POS_FRAMES) - 1
        images.append(gray_frame)
        full_color.append(frame)
        if frame_number == 0:
            last_frame = blur_gray

        if last_frame is not None and blur_gray is not None and last_frame.shape != blur_gray.shape:
            blur_gray = cv2.resize(blur_gray, (last_frame.shape[1], last_frame.shape[0]), interpolation=cv2.INTER_AREA)
            
        try:
            diff = cv2.subtract(blur_gray, last_frame)
        except Exception as err:
            print(err)
            print(frame_number, blur_gray, last_frame)
        diff_mag = cv2.countNonZero(diff)
        list_diff_mag.append(diff_mag)
        time_spans.append(curr_iter)
        last_frame = blur_gray
        curr_iter += 1

    cap.release()
    y = np.array(list_diff_mag)
    base = peakutils.baseline(y, 2)
    indices = peakutils.indexes(y - base, threshold, min_dist=1)

    results = []
    for index, elem in enumerate(indices):
        with NamedTemporaryFile(suffix='.jpg') as temp:
            status = cv2.imwrite(temp.name, full_color[elem])
            if status:
                print('Image uploaded.')
            else:
                print("Image upload failed.")
            log_message = f"Keyframe {index+1} happened at {time_spans[elem]} sec."
            print(log_message)
            keyframe_path = f"{folder_path}/{filename_wo_ext}_{index+1}.jpg"
            results.append({"frame_url": keyframe_path, "frame_time": round(time_spans[elem], 2)})
            dest_blob = dest.blob(keyframe_path)
            dest_blob.upload_from_filename(temp.name, content_type='image/jpeg')
            dest_blob.make_public()
            print(f"Uploaded {dest_blob}")

    if os.path.exists('/tmp/video.mp4'):
        os.remove('/tmp/video.mp4')

    return results

# ONLY ENABLE WHEN ON GOOGLE CLOUD FUNCTIONS
# @functions_framework.http
def main(request: Request):
    """HTTP Cloud Function.
    Args:
    request (flask.Request): The request object.
    https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data
    Returns:
    The response text, or any set of values that can be turned into a
    Response object using make_response
    https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response.
    """
    if request.mimetype == "application/json":
        video_data = request.get_json()
    else:
        video_data = request.form

    filename = video_data['filename']
    video_path = video_data['video_path']
    user_id = video_data['user_id']

    client = storage.Client()
    source_bucket = client.get_bucket(str(os.getenv('GOOGLE_STORAGE_BUCKET_NAME')))
    source_blob = source_bucket.get_blob(video_path)

    dest_bucket = client.get_bucket(str(os.getenv('GOOGLE_STORAGE_BUCKET_NAME')))

    print(f"Extracting {source_blob}")
    if str(source_blob.name).endswith('.mp4'):
        results = keyframe_detection(user_id, filename, source_blob, dest_bucket, 0.4)
        return make_response(results)
    else:
        return make_response("File is not an mp4.", 400)


if __name__ == "__main__":
    client = storage.Client()
    source_bucket = client.get_bucket("kpid-jatim")
    source_blob = source_bucket.get_blob("uploads/63de2350984ddb64fc3d675f_True_Facts_Hippopotamus.mp4")

    dest_bucket = client.get_bucket("kpid-jatim")

    keyframe_detection("testing", "True_Facts_Hippopotamus.mp4", source_blob, dest_bucket, 0.4)