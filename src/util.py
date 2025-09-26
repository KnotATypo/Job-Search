import os
import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

root_path = os.path.realpath(__file__)[: os.path.realpath(__file__).rindex("Job-Search") + 10]


def strip_string(s: str) -> str:
    return re.sub(r"\W", "", s.lower())


def new_browser():
    options = Options()
    # options.add_argument("--headless")
    return webdriver.Chrome(options=options)
