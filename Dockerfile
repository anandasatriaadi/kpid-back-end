# pull official base image
FROM python:3.10-slim

# set work directory
WORKDIR /usr/src/app

# install dependencies
RUN apt-get update
RUN apt-get install -y ffmpeg
RUN apt-get install -y wkhtmltopdf
RUN apt-get install -y protobuf-compiler
RUN apt-get install -y p7zip-full wget git 
RUN pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

# Downloads models from tensorflow model and remove unused folders to minimize image size
RUN git clone https://github.com/tensorflow/models.git ./ai_utils/models \
    && rm -r ./ai_utils/models/community \
    ./ai_utils/models/docs \
    ./ai_utils/models/official \
    ./ai_utils/models/orbit \
    ./ai_utils/models/tensorflow_models
WORKDIR /usr/src/app/ai_utils/models/research
RUN protoc ./object_detection/protos/*.proto --python_out=.
WORKDIR /usr/src/app

# Downloads saved model
RUN wget --load-cookies \
    /tmp/cookies.txt \
    "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=1MX_B0_gX057qnQpNY9tbEHSiiO9UXjj0' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1MX_B0_gX057qnQpNY9tbEHSiiO9UXjj0" \
    -O /usr/src/app/saved_model.7z \
    && rm -rf /tmp/cookies.txt \
    && 7z x /usr/src/app/saved_model.7z -o/usr/src/app/ai_utils \
    && rm /usr/src/app/saved_model.7z

# volume
VOLUME /usr/src/app/

# copy project
COPY . /usr/src/app/

CMD [ "gunicorn", "--bind", "0.0.0.0:5000", "--timeout=0", "--workers=2", "--access-logfile", "'-'", "run:app" ]

