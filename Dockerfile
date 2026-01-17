FROM python:3.13-slim

RUN apt update && \
    apt install -y --no-install-recommends chromium-headless-shell chromium-driver curl && \
    curl -Ls https://astral.sh/uv/install.sh | sh && \
    apt purge -y curl && \
    apt autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir Job-Search
WORKDIR /Job-Search
COPY . .
RUN /root/.local/bin/uv sync

EXPOSE 3232
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/root/.local/bin/uv", "run", "host"]