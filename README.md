# Job Search

A comprehensive job search tool that automates the process of finding, filtering, and managing job listings from
multiple job sites.

## Description

Job Search is a web application that helps streamline your job hunting process. It scrapes job listings from multiple
job sites (LinkedIn, Seek, Jora, ~~Indeed~~), filters them based on your preferences, and provides a user-friendly
interface to triage, review, and track your job applications.

## Features

- **Multi-site Scraping**: Automatically scrapes job listings from LinkedIn, Seek, Jora, and Indeed
- **Customizable Search**: Configure search terms and blacklist terms
- **Workflow Management**: Three-stage workflow for job hunting:
    - **Triage**: Quickly filter through new job listings
    - **Reading**: Review jobs you're interested in
    - **Applying**: Track jobs you're applying to
- **Automatic Filtering**: Automatically filter out jobs with blacklisted terms in the title
- **Dark Mode**: Always-on dark mode to reduce eye strain and provide a modern interface

## Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL database
- Chrome or Chromium browser (for web scraping)

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/knotatypo/Job-Search.git
   cd Job-Search
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up the database:
   ```
   CREATE DATABASE job_search;
   CREATE USER 'dev'@'localhost' IDENTIFIED BY 'password';
   GRANT ALL PRIVILEGES ON job_search.* TO 'dev'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

## Usage

### Downloading Job Listings

Run the download script to fetch new job listings:

```
python src/download.py
```

### Managing Job Listings

#### Flask UI

```
python src/flask_app.py
```

Then open your browser and navigate to http://127.0.0.1/

The UI provide functionality with three main sections:

1. **Triage**: Review new job listings and mark them as "interested" or "not interested"

2. **Reading**: Review jobs marked as "interested" and open them on the original job site

3. **Applying**: Track jobs you're applying to

## Database Structure

The application uses a PostgreSQL database with the following tables:

- **blacklistterm**: Stores blacklist terms for filtering job titles
- **job**: Stores job information (title, company, type, status)
- **jobtolisting**: Maps jobs to listings (one-to-many relationship)
- **listing**: Stores listing information from different job sites
- **pagecount**: Tracks the number of pages scraped for each site and query
- **searchterm**: Stores search terms for each user
- **user**: Stores user IDs

## Dependencies

- `selenium-stealth`
- `beautifulsoup4`
- `tqdm`
- `selenium`
- `peewee`
- `transformers`
- `flask`
- `waitress`
- `psycopg2-binary`

## Disclaimer

Much of the front-end code, particularly the CSS and HTML is written by a combination of LLMs including JetBrains Junie
and GitHub Copilot.