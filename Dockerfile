FROM python:3.10.9-slim-buster

WORKDIR /

RUN mkdir ./app
RUN mkdir ./creds

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY ./app ./app

CMD [ "python3", "-u", "-m", "app"]
