FROM python:3.9-slim

WORKDIR /src

COPY ./src/ .

RUN pip install -r requirements.txt

EXPOSE 3978

HEALTHCHECK CMD curl --fail http://localhost:3978/_stcore/health || exit 1

CMD ["gunicorn", "--bind=0.0.0.0:3978", "--worker-class=aiohttp.worker.GunicornWebWorker", "--timeout=600", "app:app"]