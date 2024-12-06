from enum import Enum
from typing import List, Tuple

from tqdm import tqdm

from model import PageCount, Job, Listing, JobToListing
from util import strip_string, root_path

HTML_PARSER = "html.parser"


class JobType(Enum):
    FULL = "full"
    PART = "part"
    CASUAL = "casual"


class Site:
    PAGE_URL: str
    LISTING_URL: str
    SITE_STRING: str

    def __init__(self, page_url: str, listing_url: str, site_string: str) -> None:
        self.PAGE_URL = page_url
        self.LISTING_URL = listing_url
        self.SITE_STRING = site_string.lower()

    def download_new_listings(self, query: str, job_type: JobType) -> None:
        page_count: PageCount = PageCount.get_or_create(site=self.SITE_STRING, query=query, type=job_type.value)[0]
        expected_pages = page_count.pages

        page = 0
        with tqdm(
            total=expected_pages,
            desc=f"{self.SITE_STRING} - {query} - {job_type.value}",
            unit="page",
            leave=False,
        ) as pbar:
            while True:
                listings = self.get_listings_from_page(page, query, job_type)
                if len(listings) == 0:
                    break
                self.save_listings(listings)
                page += 1
                if page > expected_pages:
                    pbar.total += 1
                pbar.update()

        page_count.pages = page
        page_count.save()

    def save_listings(self, listings: List[Tuple[Listing, Job]]):
        new_listings = []
        for listing, job in listings:
            listing, created = Listing.get_or_create(id=listing.id, site=listing.site)
            if created:
                new_listings.append((listing, job))
                description = self.get_listing_description(listing.id)
                with open(f"{root_path}/job_descriptions/{listing.id}.txt", "w+") as f:
                    description_utf = description.encode("utf-8", "ignore").decode("utf-8", "ignore")
                    f.write(description_utf)

        jobs: List[Job] = Job.select()
        existing_map = {strip_string(j.title) + "-" + strip_string(j.company): j.id for j in jobs}
        for listing, job in new_listings:
            new_key = strip_string(job.title) + "-" + strip_string(job.company)
            if new_key in existing_map:
                JobToListing.create(job_id=existing_map[new_key], listing_id=listing.id)
            else:
                job.save()
                JobToListing.create(job_id=job.id, listing_id=listing.id)

    def build_page_link(self, page_number: int, query: str, job_type: str):
        return (
            self.PAGE_URL.replace("%%QUERY%%", query)
            .replace("%%PAGE%%", str(page_number))
            .replace("%%TYPE%%", job_type)
        )

    def get_listings_from_page(self, page_number, query: str, job_type: JobType) -> List[Tuple[Listing, Job]]:
        raise NotImplementedError

    def extract_info(self, job) -> Tuple[Listing, Job]:
        raise NotImplementedError

    def build_job_link(self, job_id) -> str:
        return self.LISTING_URL.replace("%%ID%%", str(job_id))

    def get_listing_description(self, listing_id) -> str:
        raise NotImplementedError
