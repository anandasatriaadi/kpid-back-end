import pathlib
import sys
from typing import Dict, List

import numpy as np
import psutil
import tensorflow as tf
from PIL import Image

from ai_utils.models.research.object_detection.utils import label_map_util
from app.dto import FrameResult, ModerationDecision, ModerationResult
from config import UPLOAD_PATH

# Patch the location of gfile
tf.gfile = tf.io.gfile


class ObjectDetector(object):
    def __init__(self, model_path=None):
        label_map = label_map_util.load_labelmap(f"{model_path}/SARU.pbtxt")
        categories = label_map_util.convert_label_map_to_categories(
            label_map, max_num_classes=90, use_display_name=True
        )
        self.category_index = label_map_util.create_category_index(categories)

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

        # free up memory by deleting heavy objects after use
        del image_np
        del input_tensor
        del output_dict

        return num_detections


def detect_objects(frame_results: List[FrameResult]) -> List[ModerationResult]:
    current_directory = pathlib.Path.cwd()
    violation_categories = ["saru"]

    results: Dict[str, ModerationResult] = {}
    for violation in violation_categories:
        model_path = current_directory.joinpath("ai_utils", "saved_model", violation)
        client = ObjectDetector(str(model_path))
        for frame_result in frame_results:
            print(f"\n\nDetecting {violation} {frame_result}\n\n")
            saved_file = f"{UPLOAD_PATH}/{frame_result['frame_url'].split('/')[-1]}"
            with Image.open(saved_file).convert("RGB") as image:
                model_result = client.detect(image)

            # free up memory by deleting image from memory after use
            del image

            if model_result > 0:
                if results.get(frame_result["frame_url"]):
                    results[frame_result["frame_url"]].category.append(violation)
                else:
                    results[frame_result["frame_url"]] = ModerationResult(
                        second=frame_result["frame_time"],
                        clip_url="",
                        decision=str(ModerationDecision.PENDING),
                        category=[violation],
                    )

    return list(results.values())


if __name__ == "__main__":
    process = psutil.Process()  # Get the current process
    print("Starting main method...")
    initial_memory = process.memory_info().rss / (
        1024 * 1024
    )  # Initial memory consumption
    initial_cpu = process.cpu_percent()  # Initial CPU usage

    # Run the main logic of the program
    images: List[FrameResult] = [
        FrameResult(frame_time=0.12, frame_url="True_Facts_-_Hippopotamus_2.jpg").as_dict(),
    ]

    result = detect_objects(images)

    final_memory = process.memory_info().rss / (1024 * 1024)  # Final memory consumption
    final_cpu = process.cpu_percent()  # Final CPU usage

    print("Main method finished.")
    print(f"Memory consumption: {final_memory - initial_memory:.2f} MB")
    print(f"Peak CPU usage: {final_cpu}%")
    print(f"Object detected: {result}")
    # print(detect_objects("/home/annd/test.jpg"))
