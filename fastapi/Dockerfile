FROM python:3.10.11-slim-buster

WORKDIR /src

ADD ./requirements.txt /src/

RUN pip install -r requirements.txt

COPY . /src/

CMD ["python3 -m", "server.py"]