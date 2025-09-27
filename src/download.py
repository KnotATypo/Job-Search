import json
import os
from typing import List, Tuple

from tqdm import tqdm

from model import Job, SearchTerm
from sites.indeed import Indeed
from sites.jora import Jora
from sites.linkedin import LinkedIn
from sites.seek import Seek
from sites.site import JobType, Site


def main():
    # Fetch search terms from the database as objects
    search_terms = list(SearchTerm.select())
    sites = [Indeed()]

    for site in tqdm(sites, desc="Sites", unit="site"):
        for st in tqdm(search_terms, desc="Terms", unit="term", leave=False):
            # Pass both the term and the username to the site download method
            site.download_new_listings(st.term, st.user.username)

    # easy_filter(blacklist_terms)


def easy_filter(blacklist_terms: List[str]):
    new_jobs = Job.select().where(Job.status == "new")
    for term in blacklist_terms:
        for job in new_jobs:
            if term.lower() in job.title.lower():
                job.status = "easy_filter"
                job.save()


def load_config() -> Tuple[List[str], List[str], List[Site], List[JobType]]:
    root_path = os.path.realpath(__file__)[: os.path.realpath(__file__).rindex("Job-Search") + 10]
    with open(f"{root_path}/config/config.json", "r") as f:
        config = json.load(f)

    sites = []
    for site in config["sites"]:
        match site:
            case "indeed":
                sites.append(Indeed())
            case "jora":
                sites.append(Jora())
            case "seek":
                sites.append(Seek())
            case "linkedin":
                sites.append(LinkedIn())

    types = []
    for type in config["types"]:
        match type:
            case "full":
                types.append(JobType.FULL)
            case "part":
                types.append(JobType.PART)
            case "casual":
                types.append(JobType.CASUAL)

    return config["search-terms"], config["title-blacklist"], sites, types


if __name__ == "__main__":
    main()
