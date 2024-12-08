import os
import re
import socket
from typing import TextIO

from fabric import Connection
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

root_path = os.path.realpath(__file__)[: os.path.realpath(__file__).rindex("Job-Search") + 10]


def is_server() -> bool:
    return socket.gethostname() == "jobs"


if is_server():
    sftp = Connection("jobs.lan", "josh").sftp()


def strip_string(s: str) -> str:
    return re.sub(r"\W", "", s.lower())


def new_browser():
    options = Options()
    options.add_argument("--headless")
    return webdriver.Firefox(options=options)


def open_description_file(listing_id: str) -> TextIO:
    if is_server():
        return open(f"/home/josh/Job-Search/descriptions/{listing_id}.txt", "w+")
    else:
        return sftp.open(f"Job-Search/descriptions/{listing_id}.txt", "w+")
