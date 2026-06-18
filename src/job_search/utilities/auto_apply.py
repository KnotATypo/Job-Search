"""
Process to automatically apply for jobs using Seeks "Quick Apply" function.
This runs every 6 hours and will ignore any listings/jobs that are already in the db - i.e. it will only consider new postings.

For each new listing, there are 3 outcomes:
- Saved: The listing has no quick apply and is instead sent through the regular pipeline
- Applied: The listing has been applied to using the quick apply
- Pending: The listing has a quick apply, but there are one or more unanswered questions to fill

The results are then sent in a Discord message along with the links for any pending listings
"""

import datetime
import functools
import operator
import time
from typing import List, Set

import requests
from bs4 import BeautifulSoup
from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from job_search.model import SearchQuery, Listing, JobStatus, Status, User, Job, db
from job_search.sites.linkedin import LinkedIn
from job_search.sites.seek import Seek
from job_search.utilities.driver_util import seek_login, driver_pool, linkedin_login
from job_search.utilities.job_util import pass_blacklist
from job_search.utilities.logger import configure_logging, logger

SEEK_CONTINUE_BUTTON = 'button[data-testid="continue-button"]'

Seek = Seek()
LinkedIn = LinkedIn()


configure_logging()


def run_applier(user: User):
    timestamp = datetime.datetime.now().isoformat() + "+10:00"
    logger.info(f"Starting applier at {timestamp}")

    logger.info("Looking for new listings")
    listings = get_listings(user)

    logger.info("Logging in to Seek")

    logger.info("Attempting applications")
    statuses = {"pending": [], "saved": [], "applied": [], "applied_old": []}
    for listing in listings:
        if listing.site.name == "Seek":
            status = seek_attempt_application(listing, user)
        elif listing.site.name == "LinkedIn":
            status = linkedin_attempt_application(listing, user)
        else:
            raise NotImplementedError(f"Site {listing.site} is not supported for auto-application")

        if status in ["applied", "applied_old"]:
            update_status(listing, Status.AUTO_APPLIED, user)
        if status in ["pending"]:
            update_status(listing, Status.AUTO_NEW, user)

        statuses[status].append(listing)

    logger.info(
        f"Applier run complete with: Applied - {len(statuses["applied"])}, Pending - {len(statuses["pending"])}, Saved - {len(statuses["saved"])}"
    )


def update_status(listing: Listing, new_status: Status, user: User):
    # Create status before saving them so they aren't saved as NEW
    job_status, created = JobStatus.get_or_create(job=listing.job, user=user, defaults={"status": new_status})
    if not created:
        job_status.status = new_status
        job_status.save()


def update_pending(user):
    pending = (
        JobStatus.select()
        .join(Job)
        .join(Listing)
        .where(
            JobStatus.status == Status.AUTO_NEW,
            JobStatus.user == user,
            Listing.site.name == "Seek",
        )
    )

    pending_listings: List[List[Listing]] = [list(x.job.listing_set) for x in pending]
    for listings in pending_listings:
        for l in listings:
            result = seek_attempt_application(l, user)
            if result == "applied_old":
                update_status(l, Status.AUTO_APPLIED, user)
            elif l.timestamp < datetime.datetime.now() - datetime.timedelta(days=5):
                # If this listing is more than 5 days old, move it on it a normal listing
                JobStatus.get(job=l.job, user=user).delete_instance()


def notify_user(user: User, since: datetime.datetime):
    """
    Send ping with information about applied jobs with links to pending jobs.
    """
    update_pending(user)

    if user.webhook_url is None:
        return
    pending = (
        JobStatus.select().join(Job).join(Listing).where(JobStatus.status == Status.AUTO_NEW, Listing.timestamp > since)
    )
    applied = (
        JobStatus.select()
        .join(Job)
        .join(Listing)
        .where(JobStatus.status == Status.AUTO_APPLIED, Listing.timestamp > since)
    )

    links_for_pending = ""
    for job_status in pending:
        for listing in job_status.job.listing_set:
            if listing.site.name == "Seek":
                links_for_pending += Seek.build_listing_link(listing) + "\n"
            # elif listing.site.name == "LinkedIn":
            #     links_for_pending += LinkedIn.build_listing_link(listing) + "\n"

    response = requests.post(
        user.webhook_url,
        json={
            "embeds": [
                {
                    "title": "Job Bot Auto-Applier",
                    "description": links_for_pending,
                    "fields": [
                        {"name": "Applied", "value": len(applied), "inline": True},
                        {"name": "Pending", "value": len(pending), "inline": True},
                    ],
                    "timestamp": since.strftime("%Y-%m-%d %H:%M:%S"),
                }
            ]
        },
    )

    response.raise_for_status()
    logger.debug("Discord ping sent")


def seek_attempt_application(listing: Listing, user: User) -> str:
    """
    Attempt to "Quick Apply" to the given listing
    """
    with driver_pool.provide() as slot:
        if not slot.seek_loggedin:
            seek_login(user, slot)

        driver = slot.driver
        driver.get(Seek.build_listing_link(listing))
        time.sleep(1)

        # Look for apply button
        try:
            apply_button = driver.find_element(By.CSS_SELECTOR, 'a[data-automation="job-detail-apply"]')
        except NoSuchElementException:
            # There is no apply button, so the job has already been applied to
            driver.find_element(By.CSS_SELECTOR, 'span[id="applied-date-message"]')
            logger.debug(f"Listing {listing.id} has already been applied to")
            return "applied_old"

        if apply_button.text == "Apply⁠":
            logger.debug(f"Listing {listing.id} has no quick apply")
            return "saved"
        elif apply_button.text != "Quick apply":
            logger.error(f'Apply button has unrecognised value "{apply_button.text}"')
            raise NotImplementedError
        apply_button.click()

        driver.find_element(By.CSS_SELECTOR, 'input[data-testid="coverLetter-method-none"]').click()
        driver.find_element(By.CSS_SELECTOR, SEEK_CONTINUE_BUTTON).click()
        time.sleep(1)

        if "Answer employer questions" in driver.page_source:
            driver.find_element(By.CSS_SELECTOR, SEEK_CONTINUE_BUTTON).click()
            try:
                WebDriverWait(driver, 1).until(
                    ec.presence_of_element_located((By.CSS_SELECTOR, 'div[id="errorPanel"]'))
                )
                logger.debug(f"Listing {listing.id} requires user input")
                return "pending"
            except TimeoutException:
                pass

        driver.find_element(By.CSS_SELECTOR, SEEK_CONTINUE_BUTTON).click()
        driver.find_element(By.CSS_SELECTOR, 'button[data-testid="review-submit-application"]').click()
    logger.debug(f"Listing {listing.id} has been applied to")

    return "applied"


def linkedin_attempt_application(listing: Listing, user: User) -> str:
    with driver_pool.provide() as slot:
        if not slot.linkedin_loggedin:
            linkedin_login(user, slot)

        driver = slot.driver
        driver.get(LinkedIn.build_listing_link(listing) + "apply/")
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        if "The job you were looking for was not found. Redirecting you to the home page" in soup.text:
            # Occasionally the page doesn't load properly, and it tries to redirect us to the home page
            return "pending"

        if element_present(driver, 'div[class="post-apply-timeline"]'):
            return "applied_old"

        try:
            while True:
                driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Continue to next step"]').click()
                if element_present(driver, 'li-icon[type="error-pebble-icon"]'):
                    return "pending"
        except NoSuchElementException:
            pass

        try:
            driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Review your application"]').click()
            if element_present(driver, 'li-icon[type="error-pebble-icon"]'):
                return "pending"
        except NoSuchElementException:
            pass

        try:
            driver.find_element(By.CSS_SELECTOR, 'label[for="follow-company-checkbox"]').click()
            driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Submit application"]').click()
        except NoSuchElementException:
            return "pending"

        time.sleep(3)
    return "applied"


def get_listings(user: User) -> set[Listing]:
    queries = list(SearchQuery.select().where(SearchQuery.auto_apply == True, SearchQuery.user == user))
    listings = set()

    # Collect listings
    for site in [Seek]:
        for q in queries:
            last_length = -1
            page = 0
            while last_length != len(listings):
                last_length = len(listings)
                listings.update(site.get_listings_from_page(q, page))
                page += 1

    # Remove existing listings
    existing_jobs = set(
        Job.select().join(JobStatus).where(JobStatus.user == user, Job.id << [l.job.id for l in listings])
    )
    existing_listings = functools.reduce(operator.iconcat, [list(j.listing_set) for j in existing_jobs], [])
    temp = listings - set(existing_listings)
    logger.info(f"Found {len(listings)} listings, {len(temp)} new listings")
    listings = temp

    # Run blacklist
    blacklisted_listings: Set[Listing] = set()
    for listing in listings:
        if not pass_blacklist(listing.job, user, auto_applier=True):
            update_status(listing, Status.BLACKLIST, user)
            blacklisted_listings.add(listing)
    listings -= blacklisted_listings
    logger.info(f"{len(listings)} listings passed blacklist")

    return listings


def element_present(driver, selector: str) -> bool:
    try:
        WebDriverWait(driver, 1).until(ec.presence_of_element_located((By.CSS_SELECTOR, selector)))
        return True
    except TimeoutException:
        return False


if __name__ == "__main__":
    with db.connection_context():
        run_applier(User.get_by_id(1))
