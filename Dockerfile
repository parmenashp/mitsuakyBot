FROM python:3.11.10-slim-bullseye

ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_DEFAULT_TIMEOUT=100

WORKDIR /bot

RUN apt-get update && apt-get install -y git gcc

RUN pip install "poetry"

COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction

COPY prisma/schema.prisma ./prisma/

RUN prisma generate

COPY ./src .

COPY settings.toml .

ENTRYPOINT ["doppler", "run", "--"]

CMD ["python", "main.py"]