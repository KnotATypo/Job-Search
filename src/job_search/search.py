from collections import defaultdict

from tqdm import tqdm

from job_search.model import BlacklistTerm
from job_search.model import Job, SearchTerm
from job_search.sites.indeed import Indeed
from job_search.sites.jora import Jora
from job_search.sites.linkedin import LinkedIn
from job_search.sites.seek import Seek


def main():
    # Fetch search terms from the database as objects
    search_terms = list(SearchTerm.select())
    sites = [Jora(), Seek(), LinkedIn()]

    for site in tqdm(sites, desc="Sites", unit="site"):
        for st in tqdm(search_terms, desc="Terms", unit="term", leave=False):
            # Pass both the term and the username to the site download method
            site.download_new_listings(st.term, st.user.username)


if __name__ == "__main__":
    main()
