FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /bot

RUN apt-get update && apt-get install -y git

RUN pip install "poetry"

COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction

COPY . .

CMD ["python", "bot.py"]