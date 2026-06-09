from typing import List

from dotenv import load_dotenv
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from tqdm import tqdm

from job_search.base_site import BaseSite
from job_search.model import Listing, Job, JobStatus, Status, User, db
from job_search.utilities.browser_util import linkedin_login, new_browser
from job_search.utilities.create_summary import create_summary
from job_search.utilities.job_util import storage, pass_blacklist
from job_search.utilities.logger import logger, progress_bars, configure_logging

load_dotenv()


def clean():
    """
    - Update blacklisting
    - Check if listings have expired
    - Download missing descriptions
    - Create summaries
    """
    configure_logging()
    logger.info("Starting clean")

    # reapply_blacklist()
    check_expired()
    missing_descriptions()
    create_summary()


def reapply_blacklist():
    logger.info("Reapplying blacklist")
    for status in tqdm(JobStatus.select(), desc="Applying Blacklists", unit="job", disable=not progress_bars):
        if pass_blacklist(status.job, status.user):
            # It shouldn't be blacklisted but is
            if status.status == Status.BLACKLIST:
                status.status = Status.NEW
        else:
            # It should be blacklisted but isn't
            if status.status == Status.NEW:
                status.status = Status.BLACKLIST
        status.save()


def check_expired():
    """
    Checks if listings have expired based on the presence of page elements determined by each site
    """
    logger.info("Checking expired listings")
    listings: List[Listing]
    listings = list(
        Listing.select(Listing, Job, JobStatus)
        .join(Job)
        .join(JobStatus)
        .where(JobStatus.status << [Status.NEW, Status.INTERESTED, Status.LIKED, Status.AUTO_NEW])
        .order_by(Listing.timestamp.asc())
    )

    driver = new_browser()
    if (driver := linkedin_login(User.get_by_id(1), driver)) is None:
        logger.warn("LinkedIn failed to login")
        driver = new_browser()
        # Remove LinkedIn listings if we failed it log in
        listings = [l for l in listings if l.site.id != "linkedin"]

    site_lookup = {l: BaseSite.get_site_instance(l.site) for l in listings}

    driver.implicitly_wait(1)
    to_expire = []
    for listing in tqdm(listings, desc="Checking expired listings", unit="listing", disable=not progress_bars):
        site: BaseSite = site_lookup[listing]
        driver.get(site.build_listing_link(listing))
        try:
            if listing.site.id == "seek":
                WebDriverWait(driver, 1).until(
                    ec.presence_of_element_located((By.CSS_SELECTOR, 'div[data-automation="expiredJobPage"]'))
                )
            elif listing.site.id == "jora":
                WebDriverWait(driver, 1).until(
                    ec.presence_of_element_located((By.CSS_SELECTOR, 'div[class="flash-container error"]'))
                )
            elif listing.site.id == "linkedin":
                WebDriverWait(driver, 1).until(
                    ec.presence_of_element_located((By.CSS_SELECTOR, 'svg[id="signal-error-small"]'))
                )
            logger.debug(f"Listing {listing.id} is expired")
            to_expire.append(listing.job)
        except TimeoutException:
            pass

    with db.connection_context():
        JobStatus.update(status=Status.EXPIRED).where(JobStatus.job << to_expire).execute()

    driver.quit()


def missing_descriptions():
    """
    Download missing descriptions.
    """
    logger.info("Downloading missing descriptions")

    listings = Listing.select().join(Job).join(JobStatus).where(JobStatus.status << [Status.NEW, Status.INTERESTED])

    clean_listings = []
    for listing in tqdm(listings, desc="Looking for Descriptions", unit="listing", disable=not progress_bars):
        if not storage.description_downloaded(listing.id):
            clean_listings.append(listing)
    listings = clean_listings

    for listing in tqdm(listings, desc="Fetching Descriptions", unit="listing", disable=not progress_bars):
        try:
            description = BaseSite.get_site_instance(listing.site).get_listing_description(listing.id)
            if description is not None:
                storage.write_description(description, listing.id)
                logger.info(f"Description saved for listing {listing.id}")
        except Exception as e:
            logger.warn(f"Error in fetching description for listing {listing.id}: {type(e).__name__} - {e}")


if __name__ == "__main__":
    clean()
