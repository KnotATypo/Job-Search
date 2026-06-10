import os
import re

from dotenv import load_dotenv

from job_search.utilities.logger import logger
from job_search.model import Job, BlacklistTerm, User
from job_search.storage import S3Storage, FileStorage, Storage

load_dotenv()

storage: Storage
if os.getenv("S3_ENDPOINT_URL") is not None:  # Default to S3 if available
    try:
        storage = S3Storage()
        logger.info(f"Using S3 for storage at: {os.getenv('S3_ENDPOINT_URL')}")
    except Exception as e:
        storage = FileStorage()
        logger.info("Unable to find S3 details. Defaulting to local file storage")
else:
    storage = FileStorage()


def get_or_create_job(title: str, company: str) -> Job:
    def _get_fuzzy_job(inner_title: str, inner_company: str) -> str:
        return (
            re.sub(r"\W", "", inner_title.lower())
            + "-"
            + re.sub(r"\W", "", inner_company.lower()).removesuffix("ptyltd")
        )

    existing_jobs = {_get_fuzzy_job(j.title, j.company): j.id for j in Job.select()}

    if (job_fuzzy := _get_fuzzy_job(title, company)) in existing_jobs:
        job = Job.get_by_id(existing_jobs[job_fuzzy])
    else:
        job = Job.create(title=title, company=company)
        logger.debug(f"Added new job {job}")

    return job


def pass_blacklist(job: Job, user: User, auto_applier=False) -> bool:
    """
    Applies the blacklist terms for the user to the given job

    job -- The job to apply the blacklist to
    """

    blacklist = (
        BlacklistTerm.select()
        .join(User, on=(BlacklistTerm.user == User.id))
        .where(User.id == user, BlacklistTerm.auto_applier == auto_applier)
    )
    for term in blacklist:
        # Title terms are case-insensitive and fuzzy, company terms are case-sensitive and exact
        if (term.type == "title" and term.term.lower() in job.title.lower()) or (
            term.type == "company" and term.term == job.company
        ):
            return False
    return True
