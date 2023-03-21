FROM python:3.9-slim AS build-env
COPY . /app
WORKDIR /app
RUN pip3 install -r requirements.txt
CMD ["python3","main.py"]