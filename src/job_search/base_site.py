import importlib
import pkgutil
import sys
from typing import List

from dotenv import load_dotenv
from tqdm import tqdm

import job_search.sites
from job_search.model import PageCount, Listing, SearchQuery, Location, JobStatus, Status
from job_search.utilities.job_util import pass_blacklist
from job_search.utilities.logger import progress_bars, logger

HTML_PARSER = "html.parser"

load_dotenv()


class NotSupportedError(Exception):
    pass


class BaseSite:
    """
    Superclass for all sites.
    """

    QUERY_URL: str
    LISTING_URL: str
    SITE_STRING: str

    def __init__(self, query_url: str, listing_url: str, site_string: str) -> None:
        """
        Constructor.

        query_url -- The URL template of search page to retrieve job listings from. The expected template parameters are %%QUERY%% where the query string goes, and %%PAGE%% where the page number goes.
        listing_url -- The URL template of individual listing to retrieve. The expect template parameter is %%ID%% where the id of the job listing goes.
        site_string -- The plain text name of the site.
        """
        self.QUERY_URL = query_url
        self.LISTING_URL = listing_url
        self.SITE_STRING = site_string.lower()

    def download_new_listings(self, query: SearchQuery) -> None:
        """
        Download new listings by iterating through pages using the QUERY_URL, incrementing the page.

        query -- The Query object containing information about the current search.
        """
        friendly_query = f"{query.term}, {query.location.name}" + (", Remote" if query.remote else "")
        page_count: PageCount = PageCount.get_or_create(site=self.SITE_STRING, query=friendly_query)[0]
        expected_pages = page_count.pages

        page_num = 0
        with tqdm(
            total=expected_pages,
            desc=f"{self.SITE_STRING} - {friendly_query}",
            unit="page",
            leave=False,
            disable=not progress_bars,
        ) as pbar:
            while True:
                listings = self.get_listings_from_page(query, page_num)
                if len(listings) == 0:
                    break

                for listing in listings:
                    # Create a status for the job if it doesn't already exist
                    JobStatus.get_or_create(
                        user=query.user,
                        job=listing.job,
                        defaults={
                            "status": Status.NEW if pass_blacklist(listing.job, query.user) else Status.BLACKLIST
                        },
                    )

                page_num += 1
                if page_num > expected_pages:
                    pbar.total += 1
                pbar.update()

        page_count.pages = page_num
        page_count.save()

        logger.info(f"Completed query {friendly_query}")

    def build_page_link(self, query: SearchQuery, page_number: int):
        """
        Builds a link to a search page using templated QUERY_URL.

        query -- The search query.
        remote -- Whether to filter for remote jobs.
        page_number -- The page number of the search. Specific incrementing rules (e.g. increments of 10) should be handled before calling this function.
        """
        query_string = self.QUERY_URL.replace("%%QUERY%%", self.adapt_term(query.term))
        query_string = query_string.replace("%%PAGE%%", str(page_number))
        query_string = self.add_location(query_string, query.location)
        if query.remote:
            query_string = self.add_remote_filter(query_string)
        if query.days_since_post != 0:
            query_string = self.add_days_filter(query_string, query.days_since_post)
        if query.auto_apply:
            query_string = self.add_quick_apply_filter(query_string)
        return query_string

    def adapt_term(self, term: str) -> str:
        """
        Adapts the given string to the format required by the given site, such as replacing spaces with %20.
        By default, just return the term.

        term -- The string to adapt.
        """
        return term

    def add_location(self, query_string: str, location: Location) -> str:
        """
        Adds the location to the query string.

        query_string -- The partially constructed query string.
        location -- The location enum to add to the query string.
        """
        raise NotImplementedError

    def get_listings_from_page(self, query: SearchQuery, page_number) -> List[Listing]:
        """
        Retrieves Listings from a given page number.

        page_number -- The page number of the search. For sites which require increments larger than +1 are handled inside this function.
        query -- The search query.
        """
        raise NotImplementedError

    def extract_info(self, listing) -> Listing:
        """
        Extracts information from BeautifulSoup page element into a Listing.

        listing -- Element to extract information from.
        """
        raise NotImplementedError

    def build_listing_link(self, listing_id) -> str:
        """
        Builds a link to an individual listing page using templated LISTING_URL.

        listing_id -- The listing id of the individual listing page.
        """
        return self.LISTING_URL.replace("%%ID%%", str(listing_id))

    def get_listing_description(self, listing_id) -> str | None:
        """
        Retrieves the description of the listing. Returns plain text.
        """
        raise NotImplementedError

    def add_remote_filter(self, query_string: str) -> str:
        """
        Adds a remote work filter to the query string.

        query_string -- The original query string.
        """
        raise NotImplementedError

    def add_days_filter(self, query_string: str, days: int) -> str:
        """
        Add a "days since posted" filter to the query string.

        query_string -- The original query string.
        """
        raise NotImplementedError

    def add_quick_apply_filter(self, query_string: str) -> str:
        """
        Add a "quick apply"/"one click apply" filter to the query string.

        query_string -- The original query string.
        """
        raise NotImplementedError

    @classmethod
    def get_site_instance(cls, site_name: str):
        """
        Gets an instance of the site class corresponding to the given site.

        site_string -- The plain text name of the site.
        """
        for _, module_name, _ in pkgutil.iter_modules(job_search.sites.__path__):
            mod_name = f"job_search.sites.{module_name}"
            if mod_name not in sys.modules:
                importlib.import_module(mod_name)

        site_string = site_name.lower()
        site_classes = {cls.__name__.lower(): cls for cls in BaseSite.__subclasses__()}
        if site_string not in site_classes:
            raise NotSupportedError(f"Site {site_string} is not supported.")
        # noinspection PyCallingNonCallable
        return site_classes[site_string]()
