from tqdm import tqdm

from job_search.model import SearchQuery
from job_search.sites.jora import Jora
from job_search.sites.linkedin import LinkedIn
from job_search.sites.seek import Seek
from job_search.sites.site import NotSupportedError


def search():
    # Fetch search queries from the database as objects
    search_queries = list(SearchQuery.select())
    sites = [Jora(), Seek(), LinkedIn()]

    for site in tqdm(sites, desc="Sites", unit="site"):
        for st in tqdm(search_queries, desc="Queries", unit="query", leave=False):
            try:
                site.download_new_listings(st)
            except NotSupportedError:
                # Some sites do not support certain filters; skip these
                pass


if __name__ == "__main__":
    search()
