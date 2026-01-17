FROM python:3.13-slim

RUN apt update && apt install wget chromium-driver chromium -y && apt clean && rm -rf /var/lib/apt/lists/* && wget -qO- https://astral.sh/uv/install.sh | sh

RUN mkdir Job-Search
WORKDIR /Job-Search
COPY . .
RUN /root/.local/bin/uv sync

EXPOSE 3232
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/root/.local/bin/uv", "run", "search"]