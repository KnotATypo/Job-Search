from typing import List

from tqdm import tqdm

from model import Job, SearchTerm
from sites.indeed import Indeed
from sites.jora import Jora
from sites.linkedin import LinkedIn
from sites.seek import Seek


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


if __name__ == "__main__":
    main()
