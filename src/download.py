from collections import defaultdict

from tqdm import tqdm

from model import BlacklistTerm
from model import Job, SearchTerm
from sites.indeed import Indeed
from sites.jora import Jora
from sites.linkedin import LinkedIn
from sites.seek import Seek


def main():
    # Fetch search terms from the database as objects
    search_terms = list(SearchTerm.select())
    sites = [Indeed(), Jora(), Seek(), LinkedIn()]

    for site in tqdm(sites, desc="Sites", unit="site"):
        for st in tqdm(search_terms, desc="Terms", unit="term", leave=False):
            # Pass both the term and the username to the site download method
            site.download_new_listings(st.term, st.user.username)

    # Fetch all blacklist terms and group by user_id
    user_blacklists = defaultdict(list)
    for bl in BlacklistTerm.select():
        user_blacklists[bl.user_id].append(bl.term)
    easy_filter(user_blacklists)


def easy_filter(user_blacklists: dict):
    new_jobs = Job.select().where(Job.status == "new")
    for job in new_jobs:
        terms = user_blacklists.get(job.user_id, [])
        for term in terms:
            if term.lower() in job.title.lower():
                job.status = "easy_filter"
                job.save()
                break  # No need to check more terms for this job


if __name__ == "__main__":
    main()
