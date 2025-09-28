from typing import Tuple, List

from model import Listing, Job
from sites.site import Site
from util import get_page_soup


class LinkedIn(Site):
    def __init__(self):
        super().__init__(
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=%%QUERY%%&start=%%PAGE%%",
            "https://www.linkedin.com/jobs/view/%%ID%%/",
            "LinkedIn",
        )

    def get_listing_description(self, listing_id) -> str:
        # TODO: Work out how to get around logging in
        return ""

    def get_listings_from_page(self, page_number, query: str) -> List[Tuple[Listing, Job]]:
        link = self.build_page_link(page_number * 10, query.replace("-", "%20"))
        soup = get_page_soup(link)
        cards = soup.find_all("li")
        if len(cards) == 0:
            return []

        jobs = [self.extract_info(card) for card in cards]

        return jobs

    def extract_info(self, job) -> Tuple[Listing, Job]:
        links = job.find_all("a")
        link = links[0]["href"]
        listing_id = link[35 : link[35:].index("?") + 35]
        title = links[0].text.strip()
        if len(links) == 1:
            company = "None"
        else:
            company = links[1].text.strip()
        return Listing(id=listing_id, site=self.SITE_STRING), Job(title=title, company=company)
