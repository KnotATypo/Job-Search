# Job Search

A comprehensive job search tool that automates the process of finding, filtering, and managing job listings from multiple job sites.

## Description

Job Search is a desktop application that helps streamline your job hunting process. It scrapes job listings from multiple job sites (LinkedIn, Seek, Jora, Indeed), filters them based on your preferences, and provides a user-friendly interface to triage, review, and track your job applications.

## Features

- **Multi-site Scraping**: Automatically scrapes job listings from LinkedIn, Seek, Jora, and Indeed
- **Customizable Search**: Configure search terms, job types, and blacklist terms
- **Workflow Management**: Three-stage workflow for job hunting:
  - **Triage**: Quickly filter through new job listings
  - **Reading**: Review jobs you're interested in
  - **Applying**: Track jobs you're applying to
- **Keyboard Shortcuts**: Efficient keyboard shortcuts for quick triage
- **Automatic Filtering**: Automatically filter out jobs with blacklisted terms in the title
- **Dark Mode**: Always-on dark mode to reduce eye strain and provide a modern interface

## Installation

### Prerequisites

- Python 3.10 or higher
- MySQL database
- Chrome or Chromium browser (for web scraping)

### Steps

1. Clone the repository:
   ```
   git clone https://github.com/knotatypo/Job-Search.git
   cd Job-Search
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up the MySQL database:
   ```
   mysql -u root -p
   CREATE DATABASE job_search;
   CREATE USER 'dev'@'localhost' IDENTIFIED BY 'password';
   GRANT ALL PRIVILEGES ON job_search.* TO 'dev'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

## Configuration

Edit the `config/config.json` file to customize your job search:

```json
{
  "sites": ["seek", "jora", "linkedin"],  // Job sites to search
  "types": ["full", "part", "casual"],    // Job types to search for
  "search-terms": [                       // Search terms
    "programmer",
    "computer-science",
    "software-engineer",
    "software-developer"
  ],
  "title-blacklist": [                    // Terms to filter out from job titles
    ".net",
    "senior",
    "lead",
    "architect",
    // ... more terms
  ]
}
```

## Usage

### Downloading Job Listings

Run the download script to fetch new job listings:

```
python src/download.py
```

### Managing Job Listings

#### Tkinter UI (Original)

Launch the original Tkinter UI:

```
python src/app.py
```

#### Flask UI (Alternative)

Alternatively, you can use the Flask-based web interface:

```
python src/flask_app.py
```

Then open your browser and navigate to http://127.0.0.1/

Both UIs provide the same functionality with three main sections:

1. **Triage**: Review new job listings and mark them as "interested" or "not interested"
   - Press `y` to mark as interested
   - Press `n` to mark as not interested
   - Press `u` to undo the last action
   - Press `s` to view the next summary (if available)

2. **Reading**: Review jobs marked as "interested" and open them on the original job site
   - Click on the job site buttons to open the listing
   - Click "Like" to move to the applying stage
   - Click "Dislike" to remove from consideration

3. **Applying**: Track jobs you're applying to
   - Click "Open" to view the job listing
   - Click "Applied" once you've submitted an application
   - Click "Ignore" to remove from consideration

## Database Structure

The application uses a MySQL database with the following tables:

- **Job**: Stores job information (title, company, type, status)
- **Listing**: Stores listing information from different job sites
- **JobToListing**: Maps jobs to listings (many-to-many relationship)
- **PageCount**: Tracks the number of pages scraped for each site, query, and job type

## Dependencies

- `requests`: HTTP requests
- `beautifulsoup4`: HTML parsing
- `tqdm`: Progress bars
- `pyppeteer` and `selenium`: Browser automation
- `peewee`: ORM for database operations
- `transformers` and `accelerate`: Machine learning for text processing
- `fabric`: Remote execution and deployment
- `pymysql`: MySQL database connector
- `flask`: Web framework for the alternative UI
