from typing import Tuple, List

from bs4 import BeautifulSoup

from model import Listing, Job
from sites.site import Site, HTML_PARSER, JobType
from util import new_browser


class LinkedIn(Site):
    def __init__(self):
        super().__init__(
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=%%QUERY%%&location=brisbane&start=%%PAGE%%&f_JT=%%TYPE%%",
            "https://www.linkedin.com/jobs/view/%%ID%%/",
            "LinkedIn",
        )

    def get_listing_description(self, listing_id) -> str:
        # TODO: Work out how to get around logging in
        return ""

    def get_listings_from_page(self, page_number, query: str, job_type: JobType) -> List[Tuple[Listing, Job]]:
        if job_type == job_type.CASUAL:
            return []

        browser = new_browser()
        while True:
            link = self.build_page_link(page_number * 10, query.replace("-", "%20"), job_type.value[0].upper())
            browser.get(link)
            soup = BeautifulSoup(browser.page_source, HTML_PARSER)
            if browser.page_source == "<html><head></head><body></body></html>":
                return []
            cards = soup.find_all("li")
            if len(cards) != 0:
                break
        browser.close()

        jobs = [self.extract_info(card) for card in cards]
        for j in jobs:
            j.type = job_type.value
        return jobs

    def extract_info(self, job) -> Tuple[Listing, Job]:
        links = job.find_all("a")
        link = links[0]["href"]
        listing_id = link[34 : link[34:].index("?") + 34]
        title = links[0].text.strip()
        if len(links) == 1:
            company = "None"
        else:
            company = links[1].text.strip()
        return Listing(id=listing_id, site=self.SITE_STRING), Job(title=title, company=company)
