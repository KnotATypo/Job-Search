from typing import List, Tuple

from bs4 import Tag

from model import Listing, Job
from sites.site import Site
from util import get_page_soup


class Seek(Site):
    def __init__(self):
        super().__init__(
            "https://www.seek.com.au/%%QUERY%%-jobs/?page=%%PAGE%%",
            "https://www.seek.com.au/job/%%ID%%",
            "Seek",
        )

    def get_listing_description(self, listing_id) -> str:
        link = self.build_job_link(listing_id)
        soup = get_page_soup(link)
        body: Tag = soup.find("div", attrs={"data-automation": "jobAdDetails"})
        if body is None:
            return ""
        return body.contents[0].text

    def get_listings_from_page(self, page_number, query) -> List[Tuple[Listing, Job]]:
        link = self.build_page_link(page_number, query)
        soup = get_page_soup(link)
        matches = soup.find_all("a", attrs={"data-automation": "jobTitle"})
        matches = [self.extract_info(x) for x in matches]

        return matches

    def extract_info(self, job) -> Tuple[Listing, Job]:
        link = job["href"]
        listing_id = link[link.rindex("/") + 1 : link.index("?")]
        title = job.string
        company_field = job.parent.parent.parent.find("a", attrs={"data-automation": "jobCompany"})
        if company_field is not None:
            company = company_field.string
        else:
            company = "None"
        return Listing(id=listing_id, site=self.SITE_STRING), Job(title=title, company=company)
