import logging
import pathlib
import sys
import time

CURR_DIR = pathlib.Path.cwd()
sys.path.append(str(CURR_DIR))
MODEL_BASE = CURR_DIR.joinpath("ai_utils", "models", "research")
sys.path.append(str(MODEL_BASE))
sys.path.append(str(MODEL_BASE.joinpath("object_detection")))
sys.path.append(str(MODEL_BASE.joinpath("slim")))

from typing import Dict, List

import numpy as np
import psutil
import tensorflow as tf
from PIL import Image

from app.dto import FrameResult, ModerationDecision, ModerationResult
from config import UPLOAD_PATH

# Patch the location of gfile
tf.gfile = tf.io.gfile
logger = logging.getLogger(__name__)


class ObjectDetector(object):
    def __init__(self, category=None):
        model_path = CURR_DIR.joinpath("ai_utils", "saved_model", category)
        parsed_model_path = pathlib.Path(model_path)

        model = tf.saved_model.load(str(parsed_model_path))
        print("Model is loaded!")
        model = model.signatures["serving_default"]
        self.model = model

    def __load_image_into_numpy_array(self, image):
        (im_width, im_height) = image.size
        return (
            np.array(image.getdata()).reshape((im_height, im_width, 3)).astype(np.uint8)
        )

    def detect(self, image):
        image_np = self.__load_image_into_numpy_array(image)
        input_tensor = tf.convert_to_tensor(image_np)
        input_tensor = input_tensor[tf.newaxis, ...]
        output_dict = self.model(input_tensor)

        num_detections = int(output_dict.pop("num_detections"))
        output_dict = {
            key: value[0, :num_detections].numpy() for key, value in output_dict.items()
        }
        scores = output_dict["detection_scores"]

        # free up memory by deleting heavy objects after use
        del image_np
        del input_tensor
        del output_dict

        return scores, num_detections


def detect_objects(frame_results: List[FrameResult]) -> List[ModerationResult]:
    violation_categories = ["saru", "sadis"]

    process = psutil.Process()
    results: Dict[str, ModerationResult] = {}
    for category in violation_categories:
        client = ObjectDetector(category)
        initial_memory = process.memory_info().rss / (1024 * 1024)
        start_time = time.time()
        for frame_result in frame_results:
            saved_file = f"{UPLOAD_PATH}/{frame_result['frame_url'].split('/')[-1]}"
            with Image.open(saved_file).convert("RGB") as image:
                model_scores, _ = client.detect(image)

            # free up memory by deleting image from memory after use
            del image

            # check whether current frame detections has any score >= 0.7
            detected_valid = any(score >= 0.7 for score in model_scores)

            if detected_valid is True:
                if results.get(frame_result["frame_url"]):
                    logger.error(results[frame_result["frame_url"]])
                    results[frame_result["frame_url"]].category.append(category.upper())
                else:
                    results[frame_result["frame_url"]] = ModerationResult(
                        second=frame_result["frame_time"],
                        clip_url="",
                        decision=str(ModerationDecision.PENDING),
                        category=[category.upper()],
                    )
                    logger.error(results[frame_result["frame_url"]])
        final_memory = process.memory_info().rss / (1024 * 1024)
        logger.info(f"Detection of {category} took {time.time() - start_time} seconds and uses {final_memory - initial_memory} MB of memory.")

    results_list = list(results.values())
    results_list.sort(key=lambda x: x.second)
    return results_list


if __name__ == "__main__":
    process = psutil.Process()  # Get the current process
    print("Starting main method...")
    initial_memory = process.memory_info().rss / (
        1024 * 1024
    )  # Initial memory consumption
    initial_cpu = process.cpu_percent()  # Initial CPU usage

    # Run the main logic of the program
    images: List[FrameResult] = [
        FrameResult(
            frame_time=0.12, frame_url="True_Facts_Hippopotamus_10.jpg"
        ).as_dict()
    ]

    result = detect_objects(images)

    final_memory = process.memory_info().rss / (1024 * 1024)  # Final memory consumption
    final_cpu = process.cpu_percent()  # Final CPU usage

    print("Main method finished.")
    print(f"Memory consumption: {final_memory - initial_memory:.2f} MB")
    print(f"Peak CPU usage: {final_cpu}%")
    print(f"Object detected: {result}")
    # print(detect_objects("/home/annd/test.jpg"))
