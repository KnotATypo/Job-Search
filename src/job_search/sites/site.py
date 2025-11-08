import os
import re
from typing import List, Tuple

from dotenv import load_dotenv
from tqdm import tqdm

from job_search import util
from job_search.model import PageCount, Job, Listing, JobToListing

HTML_PARSER = "html.parser"

load_dotenv()


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

    def download_new_listings(self, query: str, username: str) -> None:
        """
        Download new listings by iterating through pages using the QUERY_URL, incrementing the page.

        query -- The search query.
        username -- The username of the user to retrieve listings for.
        """
        page_count: PageCount = PageCount.get_or_create(site=self.SITE_STRING, query=query)[0]
        expected_pages = page_count.pages

        page = 0
        with tqdm(
            total=expected_pages,
            desc=f"{self.SITE_STRING} - {query}",
            unit="page",
            leave=False,
        ) as pbar:
            while True:
                listings = self.get_listings_from_page(page, query)
                if len(listings) == 0:
                    break
                self.save_listings(listings, username)
                page += 1
                if page > expected_pages:
                    pbar.total += 1
                pbar.update()

        page_count.pages = page
        page_count.save()

    def save_listings(self, listings: List[Tuple[Listing, Job]], username):
        """
        Saves the provided listings and jobs into the database and writes the body of the listing to the filesystem.

        listings -- List of tuples pairing Listings to their Job.
        username -- The username of the user to save the jobs for.
        """

        def strip_string(s: str) -> str:
            return re.sub(r"\W", "", s.lower())

        def get_fuzzy_job(job: Job) -> str:
            return strip_string(job.title) + "-" + strip_string(job.company)

        existing_jobs = Job.select().where(Job.username == username)
        # Sometimes job titles/companies have different casing/punctuation
        existing_jobs = {get_fuzzy_job(j): j.id for j in existing_jobs}
        for listing, job in listings:
            job.username = username
            job_fuzzy = get_fuzzy_job(job)

            if (existing_listing := Listing.get_or_none(id=listing.id, site=listing.site)) is None:
                listing = Listing.create(id=listing.id, site=listing.site, summary="")
            else:
                listing = existing_listing
            if job_fuzzy not in existing_jobs.keys():
                job.save()
            else:
                job = Job.get_by_id(existing_jobs[job_fuzzy])

            if JobToListing.get_or_none(listing=listing.id, job=job.id) is None:
                JobToListing.create(job_id=job.id, listing_id=listing.id)

            if not os.path.exists(f"{os.getenv("DATA_DIRECTORY")}/{listing.id}.txt"):
                # Sometimes even if the listing exists, the file might not
                util.write_description(listing, self)

    def build_page_link(self, page_number: int, query: str):
        return self.QUERY_URL.replace("%%QUERY%%", query).replace("%%PAGE%%", str(page_number))

    def get_listings_from_page(self, page_number, query: str) -> List[Tuple[Listing, Job]]:
        """
        Retrieves (Listing, Job) tuples from a given page number.

        page_number -- The page number of the search. For sites which require increments larger and +1 are handled inside this function.
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

    @classmethod
    def get_url(cls, job_id) -> str:
        """Return the URL for a job listing given its ID."""
        instance = cls()
        return instance.build_job_link(job_id)
