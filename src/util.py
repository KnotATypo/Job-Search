import os
import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth

root_path = os.path.realpath(__file__)[: os.path.realpath(__file__).rindex("Job-Search") + 10]


def strip_string(s: str) -> str:
    return re.sub(r"\W", "", s.lower())


def new_browser():
    options = Options()
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
