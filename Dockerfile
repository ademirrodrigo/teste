FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./

RUN apt-get update \ 
    && apt-get install -y --no-install-recommends build-essential libxml2-dev libxslt1-dev \ 
    && pip install --upgrade pip \ 
    && pip install -r requirements.txt \ 
    && apt-get purge -y build-essential \ 
    && apt-get autoremove -y \ 
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN mkdir -p data/xmls data/html logs certs

EXPOSE 8501

ENTRYPOINT ["/app/docker-entrypoint.sh"]
