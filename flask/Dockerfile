FROM python:3.10-slim-buster



COPY requirements.txt /src
WORKDIR /src
RUN pip3 -m install -r requirements.txt

COPY . /src

CMD ["python3 -m", "server.py"]