FROM python:3.12.0-slim

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y gcc default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /app
COPY requirements.txt /app

RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt --no-cache-dir

COPY proj/ /app
WORKDIR /app

CMD ["gunicorn", "proj.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--worker-class", "sync", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
