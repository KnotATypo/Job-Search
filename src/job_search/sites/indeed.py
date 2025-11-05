from typing import List, Tuple

from job_search.model import Listing, Job
from job_search.sites.site import Site
from job_search.util import get_page_soup


class Indeed(Site):
    def __init__(self):
        super().__init__(
            "https://au.indeed.com/jobs?q=%%QUERY%%&start=%%PAGE%%",
            "https://au.indeed.com/viewjob?jk=%%ID%%&sc=0kf%3B",
            "Indeed",
        )

    def get_listing_description(self, listing_id) -> str:
        link = self.build_job_link(listing_id)
        soup = get_page_soup(link)
        if soup.find("title").string == "Just a moment...":
            body = ""
        else:
            body = soup.find("div", attrs={"class": "jobsearch-JobComponent-description"}).text
        return body

    def get_listings_from_page(self, page_number, query) -> List[Tuple[Listing, Job]]:
        link = self.build_page_link(page_number * 10, query.replace("-", "+"))
        soup = get_page_soup(link)
        if soup.find("title").string == "Just a moment...":
            matches = []
        else:
            result = soup.find("a", attrs={"data-testid": "pagination-page-current"})
            if result is None or int(result.text) <= page_number:
                matches = []
            else:
                matches = soup.find_all("td", {"class": "resultContent"})
                matches = [self.extract_info(x) for x in matches]

        return matches

    def extract_info(self, job) -> Tuple[Listing, Job]:
        listing_id = job.find("a")["id"]
        listing_id = listing_id[listing_id.index("_") + 1 :]
        title = job.find("a").text
        company = job.find("span", {"data-testid": "company-name"}).text

        return Listing(id=listing_id, site=self.SITE_STRING), Job(title=title, company=company)
