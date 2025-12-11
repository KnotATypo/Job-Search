import os.path
from collections import defaultdict

from dotenv import load_dotenv
from tqdm import tqdm

from job_search import util
from job_search.model import Listing, BlacklistTerm, Job
from job_search.sites.jora import Jora
from job_search.sites.linkedin import LinkedIn
from job_search.sites.seek import Seek

load_dotenv()


def main():
    missing_descriptions()
    reapply_blacklist()


def reapply_blacklist():
    user_blacklists = defaultdict(list)
    for bl in BlacklistTerm.select():
        user_blacklists[bl.user.username].append(bl.term)
    # Only check new jobs in case one has slipped through and the user has progressed it
    new_jobs = Job.select().where(Job.status == "new")
    for job in tqdm(new_jobs, desc="Applying Blacklists", unit="job"):
        terms = user_blacklists.get(job.username, [])
        for term in terms:
            if term.lower() in job.title.lower():
                job.status = "easy_filter"
                job.save()
                break

    # Remove jobs from easy_filter if the blacklist term has been removed
    filtered_jobs = Job.select().where(Job.status == "easy_filter")
    for job in tqdm(filtered_jobs, desc="Removing Old Blacklists", unit="job"):
        remove_filter = True
        for term in user_blacklists[job.username]:
            if term.lower() in job.title.lower():
                remove_filter = False
                break
        if remove_filter:
            job.status = "new"
            job.save()


def missing_descriptions():
    """
    Download missing descriptions.
    """
    listings = Listing.select().where(Listing.summary == "")
    clean_listings = []
    for listing in tqdm(listings, desc="Collecting Listings", unit="listing"):
        if os.path.exists(f"{os.getenv("DATA_DIRECTORY")}/{listing.id}.txt"):
            with open(f"{os.getenv("DATA_DIRECTORY")}/{listing.id}.txt", "r") as f:
                content = f.read()
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
