FROM python:3.9-slim AS build-env
COPY . /app
WORKDIR /app
RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6 -y
RUN pip3 install -r requirements.txt
CMD ["python3","main.py"]