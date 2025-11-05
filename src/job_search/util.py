from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth


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
        with open(f"data/{listing.id}.txt", "w+") as f:
            f.write(description_utf)
    except OSError as e:
        print(f"Error writing file for listing {listing.id}: {e}")
