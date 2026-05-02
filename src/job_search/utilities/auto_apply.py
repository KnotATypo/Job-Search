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
import email
import imaplib
import re
import time
from email.header import decode_header

import requests
from selenium.common import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver import Keys
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from job_search.model import SearchQuery, Listing, JobStatus, Status, User, Job, db
from job_search.sites.seek import Seek
from job_search.utilities.logger import configure_logging, logger
from job_search.utilities.util import new_browser

SEEK = Seek()


configure_logging()


def run_applier(user: User):
    timestamp = datetime.datetime.now().isoformat() + "+10:00"
    logger.info(f"Starting applier at {timestamp}")

    logger.info("Looking for new listings")
    listings = get_listings(user)

    driver = new_browser()
    driver.implicitly_wait(5)

    logger.info("Logging in to Seek")
    login(user.email, user.email_password, driver)

    logger.info("Attempting applications")
    statuses = {"pending": [], "saved": [], "applied": [], "applied_old": []}
    for listing in listings:
        status = attempt_application(driver, listing)
        if status != "":
            statuses[status].append(listing)

    logger.info("Saving listings")
    for listing in statuses["applied"] + statuses["applied_old"]:
        # Create an AUTO_APPLIED status before saving them so they aren't saved as NEW
        status, created = JobStatus.get_or_create(job=listing.job, user=user, defaults={"status": Status.AUTO_APPLIED})
        if not created:
            status.status = Status.AUTO_APPLIED
            status.save()

    SEEK.save_listings(statuses["saved"], user)
    SEEK.save_listings(statuses["applied"], user)
    # This will usually be jobs that were "pending" then handled manually
    SEEK.save_listings(statuses["applied_old"], user)

    links_for_pending = ""
    for listing in statuses["pending"]:
        links_for_pending += SEEK.build_listing_link(listing) + "\n"

    logger.info(
        f"Applier run complete with: Applied - {len(statuses["applied"])}, Pending - {len(statuses["pending"])}, Saved - {len(statuses["saved"])}"
    )
    if user.webhook_url is not None:
        response = requests.post(
            user.webhook_url,
            json={
                "embeds": [
                    {
                        "title": "Job Bot Auto-Applier",
                        "description": links_for_pending,
                        "fields": [
                            {"name": "Applied", "value": len(statuses["applied"]), "inline": True},
                            {"name": "Pending", "value": len(statuses["pending"]), "inline": True},
                            {"name": "Saved", "value": len(statuses["saved"]), "inline": True},
                        ],
                        "timestamp": timestamp,
                    }
                ]
            },
        )
        response.raise_for_status()
        logger.debug("Discord ping sent")


def attempt_application(driver: WebDriver, listing: Listing) -> str:
    """
    Attempt to "Quick Apply" to the given listing
    """
    driver.get(SEEK.build_listing_link(listing))
    time.sleep(1)

    # Look for apply button
    try:
        apply_button = driver.find_element(By.CSS_SELECTOR, 'a[data-automation="job-detail-apply"]')
    except NoSuchElementException:
        # There is no apply button, so the job has already been applied to
        driver.find_element(By.CSS_SELECTOR, 'span[id="applied-date-message"]')
        logger.debug(f"Listing {listing} has already been applied to")
        return "applied_old"

    if apply_button.text == "Apply⁠":
        logger.debug(f"Listing {listing} has no quick apply")
        return "saved"
    elif apply_button.text != "Quick apply":
        logger.error(f'Apply button has unrecognised value "{apply_button.text}"')
        raise Exception
    apply_button.click()

    driver.find_element(By.CSS_SELECTOR, 'input[data-testid="coverLetter-method-none"]').click()
    driver.find_element(By.CSS_SELECTOR, 'button[data-testid="continue-button"]').click()
    time.sleep(1)

    if "Answer employer questions" in driver.page_source:
        driver.find_element(By.CSS_SELECTOR, 'button[data-testid="continue-button"]').click()
        try:
            WebDriverWait(driver, 1).until(ec.presence_of_element_located((By.CSS_SELECTOR, 'div[id="errorPanel"]')))
            logger.debug(f"Listing {listing} requires user input")
            return "pending"
        except TimeoutException:
            pass

    driver.find_element(By.CSS_SELECTOR, 'button[data-testid="continue-button"]').click()
    driver.find_element(By.CSS_SELECTOR, 'button[data-testid="review-submit-application"]').click()
    logger.debug(f"Listing {listing} has been applied to")

    return "applied"


def login(email_address: str, password: str, driver: WebDriver):
    driver.get("https://www.seek.com")
    register_text = driver.find_element(By.CSS_SELECTOR, 'span[data-automation="register-link"]')
    register_text.find_element(By.CSS_SELECTOR, "a").click()
    try:
        driver.find_element(By.CSS_SELECTOR, 'input[id="newEmailAddress"]').send_keys(email_address)
    except StaleElementReferenceException:
        driver.find_element(By.CSS_SELECTOR, 'input[id="newEmailAddress"]').send_keys(email_address)
    driver.find_element(By.CSS_SELECTOR, 'button[data-cy="register"]').click()
    code_input = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="verification input"]')
    time.sleep(5)
    code = get_code(email_address, password)
    code_input.send_keys(code)
    try:
        # Check that the code isn't invalid. If invalid, try to get code 2 more times
        time.sleep(2)
        for _ in range(2):
            alert = driver.find_element(By.CSS_SELECTOR, 'div[role="alert"]')
            if alert.text == "Invalid code. Try again or click resend below.":
                logger.warn("Invalid 2FA code, trying again")
                code_input.send_keys(Keys.BACKSPACE * 6)
                code = get_code(email_address, password)
                code_input.send_keys(code)
            else:
                time.sleep(5)
        # Seek has recently moved url
        if "Welcome to our new URL" not in alert.text:
            logger.error(f"Could not validate 2FA code: {alert.text}")
            raise Exception("Could not validate 2FA code")
    except NoSuchElementException:
        logger.debug("Successfully logged in")


def get_listings(user: User) -> set[Listing]:
    queries = list(SearchQuery.select().where(SearchQuery.auto_apply == True, SearchQuery.user == user))
    listings = set()

    # Collect listings
    for q in queries:
        last_length = -1
        page = 0
        while last_length != len(listings):
            last_length = len(listings)
            listings.update(SEEK.get_listings_from_page(q, page))
            page += 1

    # Remove existing listings
    existing_listings = set(
        Listing.select()
        .join(Job)
        .join(JobStatus)
        .where(JobStatus.user == user, Listing.id << [l.id for l in listings], Listing.site == "seek")
    )
    temp = listings - existing_listings
    logger.info(f"Found {len(listings)} listings, {len(temp)} new listings")
    listings = temp

    return listings


def get_code(email_address: str, password: str) -> str:
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(email_address, password)

    code = ""
    while code == "":
        imap.select("INBOX")
        _, search_data = imap.search(None, "UNSEEN")
        ids = search_data[0].split()[-3:]

        for raw_id in reversed(ids):
            msg_id = raw_id.decode()
            # Use BODY.PEEK[] to avoid marking the message as seen on fetch
            _, msg = imap.fetch(msg_id, "(BODY.PEEK[])")
            if msg[0] is None:
                continue
            msg = email.message_from_bytes(msg[0][1])

            subject, _ = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                continue

            logger.debug(f"Email {msg_id}: {subject}")
            if re.match(r"\d{6} is your code for SEEK", subject) is not None:
                code = subject[:6]
                imap.store(msg_id, "+FLAGS", "\\Deleted")
                break

    imap.close()
    imap.logout()

    return code


if __name__ == "__main__":
    with db.connection_context():
        run_applier(User.get_by_id(1))
