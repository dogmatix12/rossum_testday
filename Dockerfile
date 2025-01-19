FROM python:3.12-slim-bookworm

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN apt update \
    && apt install -y build-essential \
    && pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-root \
    && apt --purge -y autoremove build-essential

ENV PYTHONPATH=/app

COPY . .
    
ENTRYPOINT ["poetry", "run", "pytest"]