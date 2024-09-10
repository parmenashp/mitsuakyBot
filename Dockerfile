FROM python:3.11.8-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /bot

RUN apt-get update && apt-get install -y git gcc

RUN pip install "poetry"

COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction

COPY prisma/schema.prisma ./prisma/

RUN prisma generate

COPY ./src .

CMD ["python", "main.py"]