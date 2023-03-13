# pull official base image
FROM python:3.10.6

# set work directory
WORKDIR /usr/src/app

# install dependencies
RUN apt-get update
RUN apt-get install -y ffmpeg
RUN pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

# copy project
COPY . /usr/src/app/
