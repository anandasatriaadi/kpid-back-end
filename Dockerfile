# pull official base image
FROM python:3.10-slim

# set work directory
WORKDIR /usr/src/app

# install dependencies
RUN apt-get update
RUN apt-get install -y ffmpeg
RUN apt-get install -y wkhtmltopdf
RUN apt-get install -y protobuf-compiler
RUN pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

# volume
VOLUME /usr/src/app/

CMD [ "gunicorn", "--bind", "0.0.0.0:5000", "--timeout=0", "--workers=2", "--access-logfile", "'-'", "run:app" ]

# copy project
COPY . /usr/src/app/
