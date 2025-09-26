from typing import List, Tuple

from bs4 import BeautifulSoup, Tag
from selenium.webdriver.firefox.webdriver import WebDriver

from model import Listing, Job
from sites.site import Site, HTML_PARSER
from util import new_browser


class Indeed(Site):
    def __init__(self):
        super().__init__(
            "https://au.indeed.com/jobs?q=%%QUERY%%&start=%%PAGE%%",
            "https://au.indeed.com/viewjob?jk=%%ID%%&sc=0kf%3B",
            "Indeed",
        )

    def get_listing_description(self, listing_id) -> str:
        retry_count = 0
        while True:
            browser = new_browser()
            browser.get(self.build_job_link(listing_id))
            soup = BeautifulSoup(browser.page_source, features=HTML_PARSER)
            if soup.find("title").string != "Just a moment...":
                break
            retry_count += 1
            if retry_count > 10:
                browser.close()
                return ""
        body: Tag = soup.find("div", attrs={"class": "jobsearch-JobComponent-description"})
        browser.close()
        return body.text

    def get_listings_from_page(self, page_number, query) -> List[Tuple[Listing, Job]]:
        link = self.build_page_link(page_number * 10, query.replace("-", "+"))
        retry_count = 0
        while True:
            browser = new_browser()
            browser.get(link)
            content = browser.page_source
            soup = BeautifulSoup(content, features=HTML_PARSER)
            if soup.find("title").string != "Just a moment...":
                break
            retry_count += 1
            if retry_count > 10:
                browser.close()
                return []
        browser.close()

        result = soup.find("a", attrs={"data-testid": "pagination-page-current"})
        if result is None or int(result.text) <= page_number:
            return []

        matches = soup.find_all("td", {"class": "resultContent"})
        matches = [self.extract_info(x) for x in matches]

        return matches

    def extract_info(self, job) -> Tuple[Listing, Job]:
        listing_id = job.find("a")["id"]
        listing_id = listing_id[listing_id.index("_") + 1 :]
        title = job.find("a").text
        company = job.find("span", {"data-testid": "company-name"}).text

        return Listing(id=listing_id, site=self.SITE_STRING), Job(title=title, company=company)
