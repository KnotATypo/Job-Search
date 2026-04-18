from dotenv import load_dotenv
from tqdm import tqdm

from job_search import util
from job_search.create_summary import create_summary
from job_search.logger import logger, progress_bars, configure_logging
from job_search.model import Listing, Job, JobStatus, Status
from job_search.sites.base_site import BaseSite
from job_search.util import storage

load_dotenv()


def clean():
    """
    - Remove duplicate jobs
    - Update blacklisting
    - Download missing descriptions
    - Create summaries
    - Archive old descriptions
    """
    configure_logging()

    logger.info("Starting clean")
    reapply_blacklist()
    missing_descriptions()
    create_summary()


def reapply_blacklist():
    logger.info("Reapplying blacklist")
    for status in tqdm(JobStatus.select(), desc="Applying Blacklists", unit="job", disable=not progress_bars):
        if util.pass_blacklist(status.job, status.user):
            # It shouldn't be blacklisted but is
            if status.status == Status.BLACKLIST:
                status.status = Status.NEW
        else:
            # It should be blacklisted but isn't
            if status.status == Status.NEW:
                status.status = Status.BLACKLIST
        status.save()


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
