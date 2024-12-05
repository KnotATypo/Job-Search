import json
import os
from typing import List, Tuple

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from tqdm import tqdm

from sites import Seek, jora, Indeed
from model import Job


def main():
    search_terms, blacklist_terms = load_config()

    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)

    sites = [Seek(), Jora(driver), Indeed(driver)]
    for site in tqdm(sites, desc="Sites", unit="site"):
        for term in tqdm(search_terms, desc="Terms", unit="term", leave=False):
            site.download_new_listings(term)

    easy_filter(blacklist_terms)


def easy_filter(blacklist_terms: List[str]):
    for term in blacklist_terms:
        Job.update(status="easy_filter").where((Job.title.contains(term)) | (Job.status == "new")).execute()


def load_config() -> Tuple[List[str], List[str]]:
    root_path = os.path.realpath(__file__)[: os.path.realpath(__file__).rindex("Job-Search") + 10]
    with open(f"{root_path}/config/config_fulltime.json", "r") as f:
        config = json.load(f)
    return config["search-terms"], config["title-blacklist"]


if __name__ == "__main__":
    main()
