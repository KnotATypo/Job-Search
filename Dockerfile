FROM ghcr.io/astral-sh/uv:debian-slim

RUN apt update && \
    apt install -y --no-install-recommends chromium-headless-shell chromium-driver && \
    apt purge -y curl && \
    apt autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir Job-Search
WORKDIR /Job-Search
COPY . .

ENTRYPOINT ["uv", "run", "host"]