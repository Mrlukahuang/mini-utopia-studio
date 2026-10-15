FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/studio.db

WORKDIR /app

COPY deploy/family/requirements-family.txt /tmp/requirements-family.txt
# FFprobe validates actual private audio bytes before accepting a clip.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r /tmp/requirements-family.txt && \
    groupadd --gid 10001 family && \
    useradd --uid 10001 --gid 10001 --no-create-home family && \
    mkdir -p /data /movies && chown family:family /data /movies && \
    chmod 700 /movies

# Private backend only: no Streamlit UI, users' images, or Godot source.
COPY studio /app/studio

USER family
EXPOSE 8766
CMD ["python", "-m", "studio.family_api", "--port", "8766"]
