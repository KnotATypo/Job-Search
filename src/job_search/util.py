import os
import re
import tarfile

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth

from job_search.model import Job, BlacklistTerm, User

load_dotenv()

LISTING_DIRECTORY = os.getenv("DATA_DIRECTORY") + "/listings"
DATA_ARCHIVE = os.getenv("DATA_DIRECTORY") + "/data-archive.tar.gz"

archived_names = set()
if os.path.exists(DATA_ARCHIVE):
    with tarfile.open(DATA_ARCHIVE, "r") as tar:
        archived_names = set(tar.getnames())


def new_browser(headless=True) -> webdriver.Chrome:
    """
    Creates a new Chrome browser instance with the selenium_stealth additions

    headless -- Sets the headless options for the browser (default True)
    """
    options = Options()
    if headless:
        options.add_argument("--headless")
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


def write_description(listing, site) -> None:
    """
    Writes the description of the listing to the file "data/{listing.id}.txt"

    listing -- The listing to write
    site -- The site object to get the description from
    """
    description = site.get_listing_description(listing.id)
    description_utf = description.encode("utf-8", "ignore").decode("utf-8", "ignore")
    try:
        with open(description_path(listing), "w+") as f:
            f.write(description_utf)
    except OSError as e:
        print(f"Error writing file for listing {listing.id}: {e}")


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


def description_path(listing) -> str:
    """
    Returns the path to the description file for the given listing

    listing -- The listing to get the path for
    """
    return f"{LISTING_DIRECTORY}/{listing.id}.txt"


def description_downloaded(listing) -> bool:
    """
    Checks if the description file for the given listing exists

    listing -- The listing to check
    """
    if listing.id + ".txt" in archived_names:
        return True
    return os.path.exists(description_path(listing))


def get_fuzzy_job(job: Job) -> str:
    return re.sub(r"\W", "", job.title.lower()) + "-" + re.sub(r"\W", "", job.company.lower())
