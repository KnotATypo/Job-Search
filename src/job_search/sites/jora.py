import re
from typing import List, Tuple

from bs4 import Tag

from job_search.model import Listing, Job, SearchQuery, Location
from job_search.sites.site import Site, NotSupportedError
from job_search.util import get_page_soup


class Jora(Site):
    def __init__(self):
        super().__init__(
            "https://au.jora.com/j?q=%%QUERY%%&p=%%PAGE%%",
            "https://au.jora.com/job/%%ID%%",
            "Jora",
        )

    def get_listing_description(self, listing_id) -> str | None:
        link = self.build_job_link(listing_id)
        soup = get_page_soup(link)
        body: Tag = soup.find("div", attrs={"id": "job-description-container"})
        if body is not None:
            body = body.text
        return body

    def get_listings_from_page(self, query: SearchQuery, page_number: int) -> List[Tuple[Listing, Job]]:
        link = self.build_page_link(query, page_number)
        soup = get_page_soup(link)
        if soup.text.find("We have looked through all the results for you") != -1:
            return []
        last_page_number_div = soup.find_all("div", "search-results-page-number")
        if not last_page_number_div:
            return []
        last_page = int(re.findall(r"\d+", last_page_number_div[0].text)[-1])
        if page_number > last_page:
            return []
        matches = soup.find_all("a", attrs={"class": "job-link -no-underline -desktop-only show-job-description"})
        matches = [self.extract_info(x) for x in matches]

        return matches

    def adapt_term(self, term: str) -> str:
        return term.replace("-", "+")

    def add_location(self, query_string: str, location: Location) -> str:
        location_map = {
            Location.Brisbane: "Brisbane+QLD",
            Location.Perth: "Perth+WA",
            Location.Darwin: "Darwin+NT",
            Location.Hobart: "Hobart+TAS",
            Location.Adelaide: "Adelaide+SA",
            Location.Melbourne: "Melbourne+VIC",
            Location.Sydney: "Sydney+NSW",
            Location.Australia: "Australia",
        }
        return query_string + "&l=" + location_map[location]

    def extract_info(self, job) -> Tuple[Listing, Job]:
        link = job["href"]
        listing_id = link[link.rindex("/") + 1 : link.index("?")]
        title = job.text
        company = job.parent.parent.parent.parent.find("span", attrs={"class", "job-company"}).text
        return Listing(id=listing_id, site=self.SITE_STRING), Job(title=title, company=company)

    def add_remote_filter(self, query_string: str) -> str:
        raise NotSupportedError
