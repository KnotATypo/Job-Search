from tqdm import tqdm

from job_search.logger import progress_bars, configure_logging, logger
from job_search.model import SearchQuery, SiteQuery
from job_search.sites.base_site import NotSupportedError, BaseSite


def search():
    configure_logging()
    logger.info("Starting search")
    queries = list(SiteQuery.select().join(SearchQuery))
    for query in tqdm(queries, desc="Queries", unit="query", leave=False, disable=not progress_bars):
        try:
            site = BaseSite.get_site_instance(query.site)
            site.download_new_listings(query.query)
        except NotSupportedError:
            # Some sites do not support certain filters; skip these
            # TODO Disable the ability to enable these sites when the filters are enabled
            pass


if __name__ == "__main__":
    search()
