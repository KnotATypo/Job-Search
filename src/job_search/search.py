from tqdm import tqdm

from job_search.logger import progress_bars, configure_logging, logger
from job_search.model import SearchQuery, SiteQuery, Site
from job_search.sites.jora import Jora
from job_search.sites.linkedin import LinkedIn
from job_search.sites.seek import Seek
from job_search.sites.site import NotSupportedError


def search():
    configure_logging()
    logger.info("Starting search")
    queries = list(SiteQuery.select().join(SearchQuery))
    for query in tqdm(queries, desc="Queries", unit="query", leave=False, disable=not progress_bars):
        try:
            site = get_site(query.site)
            site.download_new_listings(query.query)
        except NotSupportedError:
            # Some sites do not support certain filters; skip these
            # TODO Disable the ability to enable these sites when the filters are enabled
            pass


def get_site(site: Site):
    match site.id:
        case "jora":
            return Jora()
        case "linkedin":
            return LinkedIn()
        case "seek":
            return Seek()
        case _:
            raise NotImplementedError


if __name__ == "__main__":
    search()
