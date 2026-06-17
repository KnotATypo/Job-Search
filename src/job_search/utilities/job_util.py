import os
import re
from datetime import datetime

from dotenv import load_dotenv

from job_search.model import Job, BlacklistTerm, User, Listing, JobTimestamp
from job_search.storage import S3Storage, FileStorage, Storage
from job_search.utilities.logger import logger

load_dotenv()

storage: Storage
if os.getenv("S3_ENDPOINT_URL") is not None:  # Default to S3 if available
    try:
        storage = S3Storage()
        logger.info(f"Using S3 for storage at: {os.getenv('S3_ENDPOINT_URL')}")
    except NotImplementedError as e:
        storage = FileStorage()
        logger.info("Unable to find S3 details. Defaulting to local file storage")
else:
    storage = FileStorage()


def get_or_create_listing(l_id: str, site_string: str, title: str, company: str) -> Listing:
    """
    Returns an existing listing or creates a new listing if it is new
    """
    if (listing := Listing.get_or_none(Listing.id == l_id)) is not None:
        return listing
    listing = Listing.create(id=l_id, site=site_string, job=get_or_create_job(title, company))
    logger.info(f"Created new listing {listing.id} for job {listing.job.id}")
    return listing


def get_or_create_job(title: str, company: str) -> Job:
    """
    Returns an existing job or creates a new job if it is new.
    Note: A job will be considered "new" if the last occurrence of the job was more than 14 days ago
    """

    def _get_fuzzy_job(inner_title: str, inner_company: str) -> str:
        """
        Turns the title and company into a fuzzy string by removing any non-word characters and the "ptyltd" suffix
        """
        return (
            re.sub(r"\W", "", inner_title.lower())
            + "-"
            + re.sub(r"\W", "", inner_company.lower()).removesuffix("ptyltd")
        )

    existing_jobs = {_get_fuzzy_job(j.title, j.company): j.id for j in Job.select()}

    if (job_fuzzy := _get_fuzzy_job(title, company)) in existing_jobs:
        db_job = Job.get_by_id(existing_jobs[job_fuzzy])
        # Checks if the most recent associate timestamp is less than 14 days ago
        if abs((JobTimestamp.get(job=db_job).timestamp - datetime.now()).days) <= 14:
            return db_job
    job = Job.create(title=title, company=company)
    logger.debug(f"Added new job {job.id}")

    return job


def pass_blacklist(job: Job, user: User, auto_applier=False) -> bool:
    """
    Applies the blacklist terms for the user to the given job

    job -- The job to apply the blacklist to
    """

    blacklist = BlacklistTerm.select().join(User, on=(BlacklistTerm.user == User.id)).where(User.id == user.id)
    if auto_applier:
        blacklist = blacklist.where(BlacklistTerm.auto_applier == True)
    for term in blacklist:
        # Title terms are case-insensitive and fuzzy, company terms are case-sensitive and exact
        if (term.type == "title" and term.term.lower() in job.title.lower()) or (
            term.type == "company" and term.term == job.company
        ):
            return False
    return True
