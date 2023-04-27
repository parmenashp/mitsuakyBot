FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /bot

RUN apt-get update && apt-get install -y git gcc

RUN pip install "poetry"

COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --only main  

COPY . .

CMD ["python", "bot.py"]