import os
import os.path
import shutil
import tarfile

from dotenv import load_dotenv
from tqdm import tqdm

from job_search import util
from job_search.model import Listing, Job, JobToListing
from job_search.sites.jora import Jora
from job_search.sites.linkedin import LinkedIn
from job_search.sites.seek import Seek
from job_search.util import DATA_ARCHIVE

load_dotenv()


def main():
    archive_old_descriptions()
    missing_descriptions()
    reapply_blacklist()


def archive_old_descriptions():
    """
    Archive descriptions where the associated job is marked "not_interested" or "blacklist" or the listing no longer exists.
    """

    # TODO: Find a better way to handle archiving without extracting everything each time
    if os.path.exists(DATA_ARCHIVE):
        with tarfile.open(DATA_ARCHIVE, "r") as tar:
            tar.extractall(path="temp")
    if not os.path.exists("temp"):
        os.mkdir("temp")

    for file in tqdm(os.listdir(os.getenv("DATA_DIRECTORY")), desc="Sorting Descriptions", unit="file"):
        listing = Listing.select().where(Listing.id == file.removesuffix(".txt")).first()
        job = Job.select().join(JobToListing).where(JobToListing.listing_id == file.removesuffix(".txt")).first()
        if listing is None or job.status in ["not_interested", "blacklist"]:
            shutil.move(f"{os.getenv('DATA_DIRECTORY')}/{file}", f"temp/{file}")

    with tarfile.open(DATA_ARCHIVE, "w:gz") as tar:
        for file in tqdm(os.listdir("temp"), desc="Archiving Descriptions", unit="file"):
            tar.add(f"temp/{file}", arcname=file)
    shutil.rmtree("temp")


def reapply_blacklist():
    # Set all "blacklist" jobs back to "new" before reapplying blacklists
    Job.update(status="new").where(Job.status == "blacklist").execute()

    new_jobs = Job.select().where(Job.status == "new")
    for job in tqdm(new_jobs, desc="Applying Blacklists", unit="job"):
        util.apply_blacklist(job)


def missing_descriptions():
    """
    Download missing descriptions.
    """

    # Descriptions are only used for making a summary, so only fetch for listings without a summary
    listings = Listing.select().where(Listing.summary == "")

    clean_listings = []
    for listing in tqdm(listings, desc="Collecting Listings", unit="listing"):
        path = util.description_path(listing)
        if os.path.exists(path):
            with open(path, "r") as f:
                content = f.read()
                # Sometimes descriptions are downloaded but empty or too short
                if len(content) < 10:
                    clean_listings.append(listing)
        else:
            clean_listings.append(listing)
    listings = clean_listings

    for listing in tqdm(listings, desc="Fetching Descriptions", unit="listing"):
        if listing.site == "linkedin":
            site = LinkedIn()
        elif listing.site == "jora":
            site = Jora()
        elif listing.site == "seek":
            site = Seek()
        try:
            util.write_description(listing, site)
        except Exception as e:
            print(f"Error fetching description for listing {listing.id}: {e}")


if __name__ == "__main__":
    main()
