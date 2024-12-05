from typing import List, Tuple

from bs4 import BeautifulSoup, Tag
from selenium.webdriver.firefox.webdriver import WebDriver

from model import Listing, Job
from sites.site import Site, HTML_PARSER


class Indeed(Site):
    browser: WebDriver

    def __init__(self, browser):
        super().__init__(
            "https://au.indeed.com/jobs?q=%%QUERY%%&l=Brisbane+QLD&radius=10&start=%%PAGE%%",
            "https://au.indeed.com/viewjob?jk=%%ID%%",
            "Indeed",
        )
        self.browser = browser

    def get_job_description(self, job_id) -> str | None:
        self.browser.get(self.build_job_link(job_id))
        soup = BeautifulSoup(self.browser.page_source, features=HTML_PARSER)
        body: Tag = soup.find("div", attrs={"class": "jobsearch-JobComponent-description"})
        if body is not None:
            return body.prettify()
        else:
            return None

    def get_listings_from_page(self, page_number, query) -> List[Tuple[Listing, Job]]:
        self.browser.get(self.build_page_link(query.replace("-", "+"), page_number * 10))
        content = self.browser.page_source
        soup = BeautifulSoup(content, features=HTML_PARSER)

        result = soup.find("a", attrs={"data-testid": "pagination-page-current"})
        if result is None or int(result.text) <= page_number:
            return []

        matches = soup.find_all("td", {"class": "resultContent"})
        return [self.extract_info(x) for x in matches]

    def extract_info(self, job) -> Tuple[Listing, Job]:
        listing_id = job.find("a")["id"]
        listing_id = listing_id[listing_id.index("_") + 1 :]
        title = job.find("a").text
        company = job.find("span", {"data-testid": "company-name"}).text

        return Listing(id=listing_id, site=self.SITE_STRING), Job(title=title, company=company)
