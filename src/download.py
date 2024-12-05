import json
import os
from typing import List, Tuple

from tqdm import tqdm

from model import Job
from sites.indeed import Indeed
from sites.jora import Jora
from sites.seek import Seek


def main():
    search_terms, blacklist_terms = load_config()

    sites = [Seek(), Jora(), Indeed()]
    for site in tqdm(sites, desc="Sites", unit="site"):
        for term in tqdm(search_terms, desc="Terms", unit="term", leave=False):
            site.download_new_listings(term)

    easy_filter(blacklist_terms)


def easy_filter(blacklist_terms: List[str]):
    new_jobs = Job.select().where(Job.status == "new")
    for term in blacklist_terms:
        for job in new_jobs:
            if term in job.title:
                job.status = "easy_filter"
                job.save()


def load_config() -> Tuple[List[str], List[str]]:
    root_path = os.path.realpath(__file__)[: os.path.realpath(__file__).rindex("Job-Search") + 10]
    with open(f"{root_path}/config/config_fulltime.json", "r") as f:
        config = json.load(f)
    return config["search-terms"], config["title-blacklist"]


if __name__ == "__main__":
    main()
