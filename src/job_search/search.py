from tqdm import tqdm

from job_search.model import SearchTerm
from job_search.sites.jora import Jora
from job_search.sites.linkedin import LinkedIn
from job_search.sites.seek import Seek
from job_search.sites.site import Query, NotSupportedError


def search():
    # Fetch search terms from the database as objects
    search_terms = list(SearchTerm.select())
    sites = [Jora(), Seek(), LinkedIn()]

    for site in tqdm(sites, desc="Sites", unit="site"):
        for st in tqdm(search_terms, desc="Terms", unit="term", leave=False):
            try:
                site.download_new_listings(Query(st.term, st.user, st.remote))
            except NotSupportedError:
                # Some sites do not support certain filters; skip these
                pass


if __name__ == "__main__":
    search()
