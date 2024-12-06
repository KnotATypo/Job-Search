import os
import re
import socket
from typing import TextIO

from fabric import Connection
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

root_path = os.path.realpath(__file__)[: os.path.realpath(__file__).rindex("Job-Search") + 10]
sftp = Connection("jobs.lan", "josh").sftp()


def strip_string(s: str) -> str:
    return re.sub(r"\W", "", s.lower())


def get_duplicate_status(id_source, cursor):
    status = []
    cursor.execute(f"SELECT duplicate FROM job_search WHERE id='{id_source}'")
    for id_target in str(cursor.fetchone()[0]).split(","):
        cursor.execute(f"SELECT status FROM job_search WHERE id='{id_target}'")
        status.append(cursor.fetchone()[0])
    if "applied" in status:
        return "applied"
    if "easy_filter" in status:
        return "easy_filter"
    if "interested_read" in status:
        return "interested_read"
    if "interested" in status:
        return "interested"
    if all([x == "not_interested" for x in status]):
        return "not_interested"
    if all([x == "new" for x in status]):
        return "new"
    return "???"


def new_browser():
    options = Options()
    options.add_argument("--headless")
    return webdriver.Firefox(options=options)


def open_description_file(listing_id: str) -> TextIO:
    if is_server():
        return open(f"/home/josh/Job-Search/descriptions/{listing_id}.txt", "w+")
    else:
        return sftp.open(f"Job-Search/descriptions/{listing_id}.txt", "w+")


def is_server() -> bool:
    return socket.gethostname() == "jobs"
