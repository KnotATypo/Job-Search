from typing import Tuple, List

from job_search.model import Listing, Job, SearchQuery, Location
from job_search.sites.site import Site
from job_search.util import get_page_soup


class LinkedIn(Site):
    def __init__(self):
        super().__init__(
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=%%QUERY%%&start=%%PAGE%%&geoId=101452733",
            "https://au.linkedin.com/jobs/view/%%ID%%/",
            "LinkedIn",
        )

    def get_listing_description(self, listing_id) -> str | None:
        link = self.build_job_link(listing_id)
        body = None
        error_count = 0
        while body is None and error_count < 5:
            soup = get_page_soup(link)
            body = soup.find("div", attrs={"class": "show-more-less-html__markup"})
            error_count += 1
        if body is not None:
            body = body.text
        return body

    def get_listings_from_page(self, query: SearchQuery, page_number: int) -> List[Tuple[Listing, Job]]:
        link = self.build_page_link(query, page_number * 10)
        soup = get_page_soup(link)
        cards = soup.find_all("li")
        if len(cards) == 0:
            return []

        jobs = [self.extract_info(card) for card in cards]
        jobs = [job for job in jobs if job is not None]

        return jobs

    def adapt_term(self, term: str) -> str:
        return term.replace("-", "%20")

    def add_location(self, query_string: str, location: Location) -> str:
        # As far as I can tell, these are magic numbers without meaning outside of LinkedIn
        location_map = {
            Location.Brisbane: "104468365",
            Location.Perth: "103392068",
            Location.Darwin: "102342003",
            Location.Hobart: "101413980",
            Location.Adelaide: "107042567",
            Location.Melbourne: "100992797",
            Location.Sydney: "104769905",
            Location.Australia: "101452733",
        }
        return query_string + "&geoId=" + location_map[location]

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

    def add_remote_filter(self, query_string: str) -> str:
        return query_string + "&f_WT=2"
