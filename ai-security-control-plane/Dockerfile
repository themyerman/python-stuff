# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir --upgrade pip
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[api,postgres]"

ENV ASCP_DATABASE_URL=sqlite:////data/ascp.db
ENV ASCP_ARTIFACT_ROOT=/data/artifacts
EXPOSE 8000
VOLUME ["/data"]
CMD ["ascp-serve"]
