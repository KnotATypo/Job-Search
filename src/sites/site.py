from typing import List, Tuple

from tqdm import tqdm

from model import PageCount, Job, Listing, JobToListing
from sites.indeed import Indeed
from sites.jora import Jora
from sites.seek import Seek
from util import strip_string

HTML_PARSER = "html.parser"


def save_listings(listings: List[Tuple[Listing, Job]]):
    new_listings = []
    for listing, job in listings:
        listing, created = Listing.get_or_create(id=listing.id, site=listing.site)
        if created:
            new_listings.append((listing, job))

    jobs: List[Job] = Job.select()
    existing_map = {strip_string(j.title) + "-" + strip_string(j.company): j.id for j in jobs}
    for listing, job in new_listings:
        new_key = strip_string(job.title) + "-" + strip_string(job.company)
        if new_key in existing_map:
            JobToListing.create(job_id=existing_map[new_key], listing_id=listing.id)
        else:
            job = Job.create(title=job.title, company=job.company)
            JobToListing.create(job_id=job.id, listing_id=listing.id)


class Site:
    PAGE_URL: str
    LISTING_URL: str
    SITE_STRING: str

    def __init__(self, page_url: str, listing_url: str, site_string: str) -> None:
        self.PAGE_URL = page_url
        self.LISTING_URL = listing_url
        self.SITE_STRING = site_string.lower()

    def download_new_listings(self, query) -> None:
        page_count: PageCount = PageCount.get_or_create(site=self.SITE_STRING, query=query)[0]
        expected_pages = page_count.pages

        page = 0
        with tqdm(
            total=expected_pages,
            desc=f"{self.SITE_STRING} - {query} pages",
            unit="page",
            leave=False,
        ) as pbar:
            while True:
                listings = self.get_listings_from_page(page, query)
                if len(listings) == 0:
                    break
                save_listings(listings)
                page += 1
                if page > expected_pages:
                    pbar.total += 1
                pbar.update()

        page_count.pages = page
        page_count.save()

    def get_listings_from_page(self, page_number, query) -> List[Tuple[Listing, Job]]:
        raise NotImplementedError

    def extract_info(self, job) -> Tuple[Listing, Job]:
        raise NotImplementedError

    def build_job_link(self, job_id) -> str:
        return self.LISTING_URL.replace("%%ID%%", str(job_id))

    def build_page_link(self, query, page_number):
        return self.PAGE_URL.replace("%%QUERY%%", str(query)).replace("%%PAGE%%", str(page_number))

    def get_job_description(self, job_id) -> str | None:
        raise NotImplementedError


class UnknownSiteException(Exception):
    pass


def get_site_instance(site_string, webdriver):
    if site_string == "seek":
        return Seek()
    elif site_string == "jora":
        return Jora(webdriver)
    elif site_string == "indeed":
        return Indeed(webdriver)
    else:
        raise UnknownSiteException("Unknown job site")
