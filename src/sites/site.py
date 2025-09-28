from typing import List, Tuple

from tqdm import tqdm

from model import PageCount, Job, Listing, JobToListing
from util import strip_string

HTML_PARSER = "html.parser"


class Site:
    PAGE_URL: str
    LISTING_URL: str
    SITE_STRING: str

    def __init__(self, page_url: str, listing_url: str, site_string: str) -> None:
        self.PAGE_URL = page_url
        self.LISTING_URL = listing_url
        self.SITE_STRING = site_string.lower()

    def download_new_listings(self, query: str, username: str) -> None:
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
        new_listings = []
        for listing, job in listings:
            job.username = username
            if Listing.get_or_none(id=listing.id, site=listing.site) is None:
                listing = Listing.create(id=listing.id, site=listing.site, summary="")
                new_listings.append((listing, job))
                description = self.get_listing_description(listing.id)
                description_utf = description.encode("utf-8", "ignore").decode("utf-8", "ignore")
                try:
                    with open(f"data/{listing.id}.txt", "w+") as f:
                        f.write(description_utf)
                except OSError as e:
                    print(f"Error writing file for listing {listing.id}: {e}")

        jobs: List[Job] = Job.select()
        existing_map = {strip_string(j.title) + "-" + strip_string(j.company): j.id for j in jobs}
        for listing, job in new_listings:
            new_key = strip_string(job.title) + "-" + strip_string(job.company)
            if new_key in existing_map:
                JobToListing.create(job_id=existing_map[new_key], listing_id=listing.id)
            else:
                job.save()
                JobToListing.create(job_id=job.id, listing_id=listing.id)

    def build_page_link(self, page_number: int, query: str):
        return self.PAGE_URL.replace("%%QUERY%%", query).replace("%%PAGE%%", str(page_number))

    def get_listings_from_page(self, page_number, query: str) -> List[Tuple[Listing, Job]]:
        raise NotImplementedError

    def extract_info(self, job) -> Tuple[Listing, Job]:
        raise NotImplementedError

    def build_job_link(self, job_id) -> str:
        return self.LISTING_URL.replace("%%ID%%", str(job_id))

    def get_listing_description(self, listing_id) -> str:
        raise NotImplementedError

    @classmethod
    def get_url(cls, job_id) -> str:
        """Return the URL for a job listing given its ID."""
        instance = cls()
        return instance.build_job_link(job_id)
