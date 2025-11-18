# Job Search

A comprehensive multi-user tool to streamline your job search process by automating job listing retrieval and
summarisation. Currently, it supports LinkedIn, Seek, and Jora for Australian job listings. Indeed support has been
deprecated due to increased anti-scraping measures.

## Setup

### Prerequisites

- PostgreSQL database
- Python 3.13
- Chrome or Chromium browser (for web scraping)

Setting up these prerequisites is currently outside the scope of this guide.

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

- `blacklistterm`: Terms used to filter out unwanted job listings.
- `job`: Stores job details.
- `jobtolisting`: One-to-many relationship between jobs and listings.
- `listing`: Individual job listings fetched from job sites.
- `pagecount`: Tracks pagination for job site scraping.
- `searchterm`: Terms used to search for job listings.
- `user`: Stores user information.

### .env Configuration

Create a `.env` file in the project root with the following template:

````dotenv
DATA_DIRECTORY=
SUMMARY_MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct
APP_SECRET_KEY=

DATABASE_NAME=job_search
DATABASE_USER=
DATABASE_PASSWORD=
DATABASE_HOST=
````

The existing variables are suggested defaults; modify them as needed.

- `DATA_DIRECTORY`: Directory to store job listing text.
- `SUMMARY_MODEL_NAME`: The model used for summarizing job descriptions.
- `APP_SECRET_KEY`: A secret key for the application.
- `DATABASE_*`: Database connection details.

## Usage

### Running the App

This package is run with [uv](https://docs.astral.sh/uv/). If you don't have it installed, you can follow the
appropriate instructions for your platform from
the [official documentation](https://docs.astral.sh/uv/getting-started/installation/).

The application has 4 main commands:

- `uv run search`: Fetch new job listings from configured job sites.
- `uv run host`: Start the web interface for managing job listings.
- `uv run clean`: Download missing job description texts and reapplies blacklist.
- `uv run summary`: Generate summaries for job descriptions using the specified model.

The recommended workflow is to host the web interface with a systemd service running `uv run host` and run
`uv run search` and `uv run summary` as a cronjob daily or at the desired frequency.

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