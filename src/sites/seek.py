from typing import List, Tuple

import requests
from bs4 import BeautifulSoup, Tag

from model import Listing, Job
from sites.site import Site, HTML_PARSER, JobType


class Seek(Site):
    def __init__(self):
        super().__init__(
            "https://www.seek.com.au/%%QUERY%%-jobs/in-Brisbane-CBD-&-Inner-Suburbs-Brisbane-QLD%%TYPE%%?page=%%PAGE%%",
            "https://www.seek.com.au/job/%%ID%%",
            "Seek",
        )

    def get_job_description(self, job_id) -> str | None:
        response = requests.get(self.build_job_link(job_id))
        soup = BeautifulSoup(response.text, features=HTML_PARSER)
        body: Tag = soup.find("div", attrs={"data-automation": "jobAdDetails"})
        if body is not None:
            return body.contents[0].prettify()
        else:
            return None

    def get_listings_from_page(self, page_number, query, job_type) -> List[Tuple[Listing, Job]]:
        if job_type == JobType.FULL:
            type_str = "/full-time"
        elif job_type == JobType.PART:
            type_str = "/part-time"
        elif job_type == JobType.CASUAL:
            type_str = "/casual-vacation"
        else:
            type_str = ""
        link = self.build_page_link(page_number, query, type_str)
        response = requests.get(link)
        if response.status_code != 200:
            print("The response returned a non-200 status.")

        soup = BeautifulSoup(response.text, features=HTML_PARSER)
        matches = soup.find_all("a", attrs={"data-automation": "jobTitle"})
        matches = [self.extract_info(x) for x in matches]
        for m in matches:
            m[1].type = job_type.value
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
