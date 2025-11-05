import os.path

from dotenv import load_dotenv
from tqdm import tqdm

from job_search import util
from job_search.model import Listing
from job_search.sites.jora import Jora
from job_search.sites.linkedin import LinkedIn
from job_search.sites.seek import Seek

load_dotenv()


def main():
    listings = Listing.select().where(Listing.summary == "")
    clean_listings = []
    for listing in listings:
        if os.path.exists(f"{os.getenv("DATA_DIRECTORY")}/{listing.id}.txt"):
            with open(f"{os.getenv("DATA_DIRECTORY")}/{listing.id}.txt", "r") as f:
                content = f.read()
                if len(content) < 10:
                    clean_listings.append(listing)
        else:
            clean_listings.append(listing)
    listings = clean_listings
    for listing in tqdm(listings):
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
