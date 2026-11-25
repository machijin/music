# Stage 1: build Audiveris (the sheet-music reader) from source.
FROM eclipse-temurin:25-jdk AS audiveris
ARG AUDIVERIS_VERSION=5.9.0
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch ${AUDIVERIS_VERSION} https://github.com/Audiveris/audiveris /src
WORKDIR /src
RUN ./gradlew --no-daemon :app:installDist \
 && mkdir -p /opt/audiveris \
 && cp -r app/build/install/*/* /opt/audiveris/ \
 && ls /opt/audiveris/bin

# Stage 2: viewer and playback libraries, served locally (no CDN at runtime).
FROM node:22-slim AS vendor
WORKDIR /v
COPY tools/vendor.sh /v/vendor.sh
RUN sh /v/vendor.sh /v/out

# Stage 3: the web service.
FROM eclipse-temurin:25-jre
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv fontconfig fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*
COPY --from=audiveris /opt/audiveris /opt/audiveris
RUN python3 -m venv /venv
COPY requirements.txt /app/requirements.txt
RUN /venv/bin/pip install --no-cache-dir -r /app/requirements.txt
COPY app /app/app
COPY --from=vendor /v/out /app/app/static/vendor
WORKDIR /app
ENV DATA_DIR=/data JAVA_TOOL_OPTIONS="-Djava.awt.headless=true"
VOLUME /data
EXPOSE 8000
CMD ["/venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
