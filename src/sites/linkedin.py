from typing import Tuple, List

from model import Listing, Job
from sites.site import Site
from util import get_page_soup


class LinkedIn(Site):
    def __init__(self):
        super().__init__(
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=%%QUERY%%&start=%%PAGE%%&geoId=101452733",
            "https://au.linkedin.com/jobs/view/%%ID%%/",
            "LinkedIn",
        )

    def get_listing_description(self, listing_id) -> str:
        link = self.build_job_link(listing_id)
        body = None
        error_count = 0
        while body is None and error_count < 5:
            soup = get_page_soup(link)
            body = soup.find("div", attrs={"class": "show-more-less-html__markup"})
            error_count += 1
        if body is None:
            body = ""
        else:
            body = body.text
        return body

    def get_listings_from_page(self, page_number, query: str) -> List[Tuple[Listing, Job]]:
        link = self.build_page_link(page_number * 10, query.replace("-", "%20"))
        soup = get_page_soup(link)
        cards = soup.find_all("li")
        if len(cards) == 0:
            return []

        jobs = [self.extract_info(card) for card in cards]
        jobs = [job for job in jobs if job is not None]

        return jobs

    def extract_info(self, job) -> Tuple[Listing, Job] | None:
        links = job.find_all("a")
        link = links[0]["href"]
        if "https://au" not in link:
            return None
        listing_id = link[link[: link.index("?")].rindex("/") + 1 : link.index("?")]
        title = links[0].text.strip()
        if len(links) == 1:
            company = "None"
        else:
            company = links[1].text.strip()
        return Listing(id=listing_id, site=self.SITE_STRING), Job(title=title, company=company)
