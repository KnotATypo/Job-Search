import os
import re

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth

from job_search.model import Job, BlacklistTerm, User
from job_search.storage import S3Storage, FileStorage, Storage

load_dotenv()

storage: Storage
if os.getenv("S3_ENDPOINT_URL") is not None:  # Default to S3 if available
    try:
        storage = S3Storage()
    except Exception as e:
        storage = FileStorage()
else:
    storage = FileStorage()


def new_browser(headless=True) -> webdriver.Chrome:
    """
    Creates a new Chrome browser instance with the selenium_stealth additions

    headless -- Sets the headless options for the browser (default True)
    """
    options = Options()
    if headless:
        options.add_argument("--headless")

    # Flag needed to run in Docker
    options.add_argument("--no-sandbox")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)

    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    return driver


def get_page_soup(link: str) -> BeautifulSoup:
    """
    Returns a BeautifulSoup object for the given URL

    link -- The URL to get the page from
    """
    browser = new_browser()
    browser.get(link)
    content = browser.page_source
    soup = BeautifulSoup(content, features="html.parser")
    browser.close()
    return soup


def apply_blacklist(job: Job) -> bool:
    """
    Applies the blacklist terms for the user to the given job

    job -- The job to apply the blacklist to
    """

    blacklist = BlacklistTerm.select().join(User, on=(BlacklistTerm.user == User.id)).where(User.id == job.user)
    for term in blacklist:
        # Title terms are case-insensitive and fuzzy, company terms are case-sensitive and exact
        if (term.type == "title" and term.term.lower() in job.title.lower()) or (
            term.type == "company" and term.term == job.company
        ):
            job.status = "blacklist"
            job.save()
            return True
    return False


def get_fuzzy_job(job: Job) -> str:
    return re.sub(r"\W", "", job.title.lower()) + "-" + re.sub(r"\W", "", job.company.lower())
