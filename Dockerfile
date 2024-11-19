# syntax=docker/dockerfile:1
FROM python:3.12-slim

RUN rm -f /etc/apt/apt.conf.d/docker-clean; \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update -y && apt-get upgrade -y

WORKDIR /annotations_api
ADD LICENSE requirements.txt ./
ADD annotations_api ./annotations_api/
ADD pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip pip3 install -r requirements.txt .

ENTRYPOINT ["uvicorn", "annotations_api.api:app", "--host", "0.0.0.0", "--port", "8000"]
EXPOSE 8000

