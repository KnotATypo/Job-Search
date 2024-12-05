from typing import List, Tuple

from bs4 import BeautifulSoup, Tag
from selenium.webdriver.firefox.webdriver import WebDriver

from model import Listing, Job
from sites.site import Site, HTML_PARSER, JobType
from util import new_browser


class Indeed(Site):
    browser: WebDriver

    def __init__(self):
        super().__init__(
            "https://au.indeed.com/jobs?q=%%QUERY%%&l=Brisbane+QLD&radius=10&start=%%PAGE%%",
            "https://au.indeed.com/viewjob?jk=%%ID%%&sc=0kf%3Ajt(%%TYPE%%)%3B",
            "Indeed",
        )
        self.browser = new_browser()

    def get_job_description(self, job_id) -> str | None:
        self.browser.get(self.build_job_link(job_id))
        soup = BeautifulSoup(self.browser.page_source, features=HTML_PARSER)
        body: Tag = soup.find("div", attrs={"class": "jobsearch-JobComponent-description"})
        if body is not None:
            return body.prettify()
        else:
            return None

    def get_listings_from_page(self, page_number, query, job_type) -> List[Tuple[Listing, Job]]:
        if job_type == JobType.FULL:
            type_str = "fulltime"
        elif job_type == JobType.PART:
            type_str = "parttime"
        elif job_type == JobType.CASUAL:
            type_str = "casual"
        link = self.build_page_link(page_number * 10, query.replace("-", "+"), type_str)
        retry_count = 0
        while True:
            self.browser.get(link)
            content = self.browser.page_source
            soup = BeautifulSoup(content, features=HTML_PARSER)
            if soup.find("title").string != "Just a moment...":
                break
            retry_count += 1
            if retry_count > 10:
                return []
            self.browser = new_browser()

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
