import os
import re
from dataclasses import dataclass
from typing import List, Tuple, Dict

from dotenv import load_dotenv
from tqdm import tqdm

from job_search import util
from job_search.model import PageCount, Job, Listing, JobToListing

HTML_PARSER = "html.parser"

load_dotenv()


@dataclass
class Query:
    """
    Represents a job search query.
    """

    term: str
    user_id: int
    remote: bool


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

    def download_new_listings(self, query: Query) -> None:
        """
        Download new listings by iterating through pages using the QUERY_URL, incrementing the page.

        query -- The Query object containing the search term, username, and remote filter.
        """
        friendly_query = f"{query.term}, Remote: {query.remote}"
        page_count: PageCount = PageCount.get_or_create(site=self.SITE_STRING, query=friendly_query)[0]
        expected_pages = page_count.pages

        page_num = 0
        with tqdm(
            total=expected_pages,
            desc=f"{self.SITE_STRING} - {friendly_query}",
            unit="page",
            leave=False,
        ) as pbar:
            while True:
                listings = self.get_listings_from_page(query, page_num)
                if len(listings) == 0:
                    break
                self.save_listings(listings, query.user_id)
                page_num += 1
                if page_num > expected_pages:
                    pbar.total += 1
                pbar.update()

        page_count.pages = page_num
        page_count.save()

    def save_listings(self, listings: List[Tuple[Listing, Job]], user_id: int) -> None:
        """
        Saves the provided listings and jobs into the database and writes the body of the listing to the filesystem.

        listings -- List of tuples pairing Listings to their Job.
        user_id -- The id of the user to save the jobs for.
        """

        def get_fuzzy_job(job: Job) -> str:
            return re.sub(r"\W", "", job.title.lower()) + "-" + re.sub(r"\W", "", job.company.lower())

        def write_listing(job: Job, listing: Listing, existing_jobs: Dict) -> None:
            new_job, new_listing = False, False

            if (existing_listing := Listing.get_or_none(id=listing.id, site=listing.site)) is None:
                new_listing = True
                listing = Listing.create(id=listing.id, site=listing.site, summary="")
            else:
                listing = existing_listing

            if (job_fuzzy := get_fuzzy_job(job)) not in existing_jobs.keys():
                new_job = True
                job.save()
            else:
                job = Job.get_by_id(existing_jobs[job_fuzzy])

            if new_job or new_listing:
                JobToListing.create(job_id=job.id, listing_id=listing.id)

            if new_job:
                util.apply_blacklist(job)
            elif not os.path.exists(f"{os.getenv("DATA_DIRECTORY")}/{listing.id}.txt"):
                # Sometimes even if the listing exists, the file might not
                util.write_description(listing, self)

        existing_jobs = Job.select().where(Job.user == user_id)
        # Sometimes job titles/companies have different casing/punctuation
        existing_jobs = {get_fuzzy_job(j): j.id for j in existing_jobs}
        for listing, job in listings:
            job.user = user_id
            write_listing(job, listing, existing_jobs)

    def build_page_link(self, term: str, remote: bool, page_number: int):
        """
        Builds a link to a search page using templated QUERY_URL.

        term -- The search term.
        remote -- Whether to filter for remote jobs.
        page_number -- The page number of the search. Specific incrementing rules (e.g. increments of 10) should be handled before calling this function.
        """
        query_string = self.QUERY_URL.replace("%%QUERY%%", term).replace("%%PAGE%%", str(page_number))
        if remote:
            query_string = self.add_remote_filter(query_string)
        return query_string

    def get_listings_from_page(self, query: Query, page_number) -> List[Tuple[Listing, Job]]:
        """
        Retrieves (Listing, Job) tuples from a given page number.

        page_number -- The page number of the search. For sites which require increments larger than +1 are handled inside this function.
        query -- The search query.
        """
        raise NotImplementedError

    def extract_info(self, job) -> Tuple[Listing, Job]:
        """
        Extracts information from BeautifulSoup page element into a (Listing, Job) tuple.

        job -- Element to extract information from.
        """
        raise NotImplementedError

    def build_job_link(self, job_id) -> str:
        """
        Builds a link to an individual job page using templated LISTING_URL.

        job_id -- The job id of the individual job page.
        """
        return self.LISTING_URL.replace("%%ID%%", str(job_id))

    def get_listing_description(self, listing_id) -> str:
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

    @classmethod
    def get_url(cls, job_id) -> str:
        """Return the URL for a job listing given its ID."""
        instance = cls()
        return instance.build_job_link(job_id)
