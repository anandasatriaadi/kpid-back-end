import csv
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

# ONLY ENABLE WHEN ON GOOGLE CLOUD FUNCTIONS
# import functions_framework
import pandas as pd
from flask import Request, make_response
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage

CLOUD_BUCKET = os.getenv("GOOGLE_STORAGE_BUCKET_NAME")

def get_blacklisted_words():
    df = pd.read_csv(f'gs://{CLOUD_BUCKET}/static/abusive.csv')
    df_us = pd.read_csv(f'gs://{CLOUD_BUCKET}/static/abusive.csv', header = None)

    df_us_lower = df_us.applymap(lambda x: x.lower() if isinstance(x, str) else x)
    list_data_us = df_us_lower[0].tolist()
    list_data = df['ABUSIVE'].tolist()
    list_data.extend(list_data_us)
    blacklisted_words = list_data
    return blacklisted_words


def transcribe_gcs(audio_path, client_storage):
    """Asynchronously transcribes the audio file specified by the gcs_uri."""
    blacklisted_words_list = get_blacklisted_words()

    filename = str(audio_path).split('/')[-1]
    filename_wo_ext = filename.with_suffix('')
    
    client_speech = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=f'gs://{CLOUD_BUCKET}{audio_path}')
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
        sample_rate_hertz=16000,
        enable_word_time_offsets=True,
        language_code="id-ID",
        alternative_language_codes=["en-ES", "en-US"]
    )

    operation = client_speech.long_running_recognize(config=config, audio=audio)

    response = operation.result(timeout=90)
    
    csv_filename = f'{filename_wo_ext}.csv'
    
    with NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
        temp_filepath = temp_file.name
        
        header = ['Word', 'Start_Time', 'End_Time']
        
        with open(temp_filepath, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header)
            
            for result in response.results:
                for word in result.alternatives[0].words:
                    if word.word in blacklisted_words_list:
                        new_row = [word.word, word.start_time, word.end_time]
                        writer.writerow(new_row)
                        
    bucket = client_storage.bucket(CLOUD_BUCKET)
    blob = bucket.blob(csv_filename)
    blob.upload_from_filename(temp_filepath)
    return f'CSV file uploaded to bucket: gs://{CLOUD_BUCKET}/{csv_filename}'

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
    source_bucket = client.get_bucket(str(os.getenv('GOOGLE_STORAGE_BUCKET_NAME')))
    source_blob = source_bucket.get_blob(audio_path)

    dest_bucket = client.get_bucket()

    print(f"Extracting {source_blob}")
    if str(source_blob.name).endswith('.mp3'):
        transcribe_gcs(audio_data, dest_bucket, client)
        return make_response("Done", 200)
    else:
        return make_response("File is not an mp4.", 400)