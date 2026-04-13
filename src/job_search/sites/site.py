from typing import List

from dotenv import load_dotenv
from tqdm import tqdm

from job_search import util
from job_search.logger import progress_bars, logger
from job_search.model import PageCount, Listing, SearchQuery, User, Location, JobStatus, Status
from job_search.util import storage

HTML_PARSER = "html.parser"

load_dotenv()


class NotSupportedError(Exception):
    pass


class Site:
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
                self.save_listings(listings, query.user)
                page_num += 1
                if page_num > expected_pages:
                    pbar.total += 1
                pbar.update()

        page_count.pages = page_num
        page_count.save()

        logger.info(f"Completed query {friendly_query}")

    def save_listings(self, listings: List[Listing], user: User) -> None:
        """
        Saves the provided listings into the database and writes the body of the listing to the filesystem.

        listings -- List of Listings.
        user_id -- The id of the user to save the listings for.
        """
        for listing in listings:
            # Create a status for the job if it doesn't already exist
            JobStatus.get_or_create(
                user=user,
                job=listing.job,
                defaults={"status": Status.NEW if util.pass_blacklist(listing.job, user) else Status.BLACKLIST},
            )

            if (existing_listing := Listing.get_or_none(id=listing.id)) is None:
                listing.save()
                logger.info(f"Created new listing {listing} for job {listing.job}")
            else:
                listing = existing_listing

            # Even if the listing exists, the description might not
            if not storage.description_downloaded(listing.id):
                description = self.get_listing_description(listing.id)
                if description is not None:
                    storage.write_description(description, listing.id)

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

        job -- Element to extract information from.
        """
        raise NotImplementedError

    def build_job_link(self, listing_id) -> str:
        """
        Builds a link to an individual job page using templated LISTING_URL.

        job_id -- The job id of the individual job page.
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

    @classmethod
    def get_url(cls, listing_id) -> str:
        """Return the URL for a job listing given its ID."""
        instance = cls()
        return instance.build_job_link(listing_id)
