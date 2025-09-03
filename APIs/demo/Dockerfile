FROM python:3.9.5-slim-buster

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -U -r requirements.txt

COPY src/ app/

WORKDIR app/