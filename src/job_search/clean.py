from dotenv import load_dotenv
from tqdm import tqdm

from job_search import util
from job_search.create_summary import create_summary
from job_search.logger import logger, progress_bars, configure_logging
from job_search.model import Listing, Job
from job_search.sites.jora import Jora
from job_search.sites.linkedin import LinkedIn
from job_search.sites.seek import Seek
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

    reapply_blacklist()
    missing_descriptions()
    create_summary()


def reapply_blacklist():
    blacklist_jobs = Job.select().where(Job.status == "blacklist")
    for job in tqdm(blacklist_jobs, desc="Rechecking Backlists", unit="job", disable=not progress_bars):
        if not util.apply_blacklist(job):
            job.status = "new"
            job.save()

    new_jobs = Job.select().where(Job.status == "new")
    for job in tqdm(new_jobs, desc="Applying Blacklists", unit="job", disable=not progress_bars):
        util.apply_blacklist(job)


def missing_descriptions():
    """
    Download missing descriptions.
    """

    listings = Listing.select().join(Job).where(Job.status << ["new", "interested"])

    clean_listings = []
    for listing in tqdm(listings, desc="Looking for Descriptions", unit="listing", disable=not progress_bars):
        if not storage.description_download(listing.id):
            clean_listings.append(listing)
    listings = clean_listings

    for listing in tqdm(listings, desc="Fetching Descriptions", unit="listing", disable=not progress_bars):
        site_map = {"linkedin": LinkedIn(), "seek": Seek(), "jora": Jora()}
        try:
            description = site_map[listing.site].get_listing_description(listing.id)
            if description is not None:
                storage.write_description(description, listing.id)
                logger.info(f"Description saved for listing {listing.id}")
        except Exception as e:
            logger.warn(f"Error in fetching description for listing {listing.id}: {type(e).__name__} - {e}")


if __name__ == "__main__":
    clean()
