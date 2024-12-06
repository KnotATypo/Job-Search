import asyncio
import re
from typing import List, Tuple

from bs4 import BeautifulSoup, Tag
from pyppeteer import launch
from selenium.webdriver.firefox.webdriver import WebDriver

from model import Listing, Job
from sites.site import Site, HTML_PARSER, JobType
from util import new_browser


class Jora(Site):
    browser: WebDriver

    def __init__(self):
        super().__init__(
            "https://au.jora.com/j?l=Brisbane+QLD&q=%%QUERY%%&p=%%PAGE%%&jt=%%TYPE%%",
            "https://au.jora.com/job/%%ID%%",
            "Jora",
        )
        self.browser = new_browser()

    def get_listing_description(self, listing_id) -> str:
        self.browser.get(self.build_job_link(listing_id))
        soup = BeautifulSoup(self.browser.page_source, features=HTML_PARSER)
        body: Tag = soup.find("div", attrs={"id": "job-description-container"})
        return body.text

    def get_listings_from_page(self, page_number, query, job_type) -> List[Tuple[Listing, Job]]:
        async def get(link) -> str:
            browser = await launch()
            page = await browser.newPage()
            await page.goto(link)
            page_content = await page.content()
            await browser.close()
            return page_content

        loop = asyncio.get_event_loop()
        if job_type == JobType.FULL:
            type_num = 3
        elif job_type == JobType.PART:
            type_num = 1
        elif job_type == JobType.CASUAL:
            type_num = 2
        else:
            type_num = None
        link = self.build_page_link(page_number, query.replace("-", "+"), str(type_num) if type_num else "")
        content = loop.run_until_complete(get(link))

        soup = BeautifulSoup(content, features=HTML_PARSER)
        if soup.text.find("We have looked through all the results for you") != -1:
            return []
        last_page = int(re.findall(r"\d+", soup.find_all("div", "search-results-page-number")[0].text)[-1])
        if page_number > last_page:
            return []
        matches = soup.find_all("a", attrs={"class": "job-link -no-underline -desktop-only show-job-description"})
        matches = [self.extract_info(x) for x in matches]
        for m in matches:
            m[1].type = job_type.value
        return matches

    def extract_info(self, job) -> Tuple[Listing, Job]:
        link = job["href"]
        listing_id = link[link.rindex("/") + 1 : link.index("?")]
        title = job.text
        company = job.parent.parent.parent.parent.find("span", attrs={"class", "job-company"}).text
        return Listing(id=listing_id, site=self.SITE_STRING), Job(title=title, company=company)
