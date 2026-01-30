# Job Search

A comprehensive multi-user tool to streamline your job search process by automating job listing retrieval and
summarisation. Currently, it supports LinkedIn, Seek, and Jora for Australian job listings. Indeed support has been
deprecated due to increased anti-scraping measures.

## Setup

### Prerequisites

- Python 3.13
- Chrome or Chromium browser (for web scraping)
- PostgreSQL
- Ollama

Setting up these prerequisites is currently outside the scope of this guide. If you run this application in Docker, both
PostgreSQL and Ollama are very friendly to also be run together in a docker compose.

### Database Setup

Create a PostgreSQL database and user for the application:

```
CREATE DATABASE job_search;
CREATE USER 'user'@'host' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON job_search.* TO 'user'@'host';
FLUSH PRIVILEGES;
EXIT;
```

#### Database structure

The database is initialised and managed using [peewee](https://docs.peewee-orm.com/en/latest/). The database schema is
defined in `model.py`.

The database consists of the following tables:

- `listing`: Individual job listings fetched from job sites.
- `pagecount`: Tracks pagination for job site scraping.
- `user`: Stores user information.
- `job`: Stores job details.
- `jobtolisting`: One-to-many relationship between jobs and listings.
- `searchterm`: Terms used to search for job listings.
- `blacklistterm`: Terms used to filter out unwanted job listings.

### .env Configuration

Create a `.env` file in the project root with the following template:

````dotenv
DATA_DIRECTORY=
APP_SECRET_KEY=

DATABASE_NAME=job_search
DATABASE_USER=
DATABASE_PASSWORD=
DATABASE_HOST=

OLLAMA_HOST=
SUMMARY_MODEL_NAME=qwen3:0.6b
````

The existing variables are suggested defaults; modify them as needed.

- `DATA_DIRECTORY`: Directory to store job listing text.
- `APP_SECRET_KEY`: A secret key for the application.
- `DATABASE_*`: Database connection details.
- `OLLAMA_HOST`: The host of the Ollama instance to use for summary generation.
- `SUMMARY_MODEL_NAME`: The Ollama model used for summarising job descriptions.

## Usage

### Running the App

This package is run with [uv](https://docs.astral.sh/uv/). If you don't have it installed, you can follow the
appropriate instructions for your platform from
the [official documentation](https://docs.astral.sh/uv/getting-started/installation/).

The application has 4 main commands:

- `uv run search`: Fetch new job listings from configured job sites.
- `uv run host`: Start the web interface for managing job listings.
- `uv run clean`: 
  - Remove duplicate jobs
  - Update blacklisting
  - Download missing descriptions
  - Create summaries
  - Archive old descriptions
- `uv run summary`: Generate summaries for job descriptions using the specified model.

The main `host` service is configured to run the other 3 at configured times using a build-in scheduler. Currently, this
is hard-coded, but it will be configurable in the future.

### Web Interface

The application provides an interface optimised for both desktop and mobile use. The interface is divided into four main
sections:

1. **Initial Screening**: Review new job listings and mark them as "interested" or "not interested".
2. **Detailed Review**: Review jobs marked as "interested" and open them on the original job site.
3. **Application Submission**: Finalise applications and mark jobs as "applied".
4. **Applied Jobs**: View jobs you've applied to.

The interface also allows management of search terms and blacklist terms used for filtering job titles.

## Disclaimers

There is no password authentication for users; this is intended for personal use or within a trusted group. Likewise,
there is no security against access on the open internet, so it is recommended to only run this application within a
secure local network with external access disabled or protected by Tailscale or CloudFlare Tunnel (or similar).

Much of the front-end code, particularly the CSS and HTML is written by a combination of LLMs including JetBrains Junie
and GitHub Copilot (GPT-5 mini).