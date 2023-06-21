import csv
import os
from datetime import timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

# ONLY ENABLE WHEN ON GOOGLE CLOUD FUNCTIONS
# import functions_framework
import pandas as pd
from flask import Request, make_response
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage

CLOUD_BUCKET = str(os.getenv("GOOGLE_STORAGE_BUCKET_NAME"))

def convert_duration_to_seconds(duration_time):
    if isinstance(duration_time, timedelta):
        return duration_time.total_seconds()
    else:
        hours, minutes, seconds = map(float, duration_time.split(":"))
        return hours * 3600 + minutes * 60 + seconds

def get_blacklisted_words():
    df = pd.read_csv(f'gs://{CLOUD_BUCKET}/static/abusive.csv')
    df_us = pd.read_csv(f'gs://{CLOUD_BUCKET}/static/abusive.csv', header = None)

    df_us_lower = df_us.applymap(lambda x: x.lower() if isinstance(x, str) else x)
    list_data_us = df_us_lower[0].tolist()
    list_data = df['ABUSIVE'].tolist()
    list_data.extend(list_data_us)
    blacklisted_words = list_data
    return blacklisted_words


def transcribe_gcs(audio_path):
    """Asynchronously transcribes the audio file specified by the gcs_uri."""
    blacklisted_words_list = get_blacklisted_words()

    filename = Path(str(audio_path).split('/')[-1])
    filename_wo_ext = filename.with_suffix('')
    
    client_speech = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=f'gs://{CLOUD_BUCKET}/{audio_path}')
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
        sample_rate_hertz=16000,
        enable_word_time_offsets=True,
        language_code="id-ID",
        alternative_language_codes=["en-ES", "en-US"]
    )

    operation = client_speech.long_running_recognize(config=config, audio=audio)

    response = operation.result(timeout=1800)
            
    violations = []
    for result in response.results:
        for word in result.alternatives[0].words:
            if word.word in blacklisted_words_list:
                start_time = convert_duration_to_seconds(word.start_time)
                violations.append({"word": word.word, "time": start_time})
                        
    return violations


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
        audio_data = request.get_json()
    else:
        audio_data = request.form

    audio_path = audio_data['audio_path']

    client = storage.Client()
    source_bucket = client.get_bucket(CLOUD_BUCKET)
    source_blob = source_bucket.get_blob(audio_path)

    print(f"Extracting {source_blob}")
    if str(source_blob.name).endswith('.mp3'):
        response = transcribe_gcs(audio_path)
        return make_response({'data': response}, 200)
    else:
        return make_response("File is not an mp3.", 400)