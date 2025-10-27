import os.path

from tqdm import tqdm

from model import Listing
from sites.jora import Jora
from sites.linkedin import LinkedIn
from sites.seek import Seek


def main():
    listings = Listing.select().where(Listing.summary == "")
    clean_listings = []
    for listing in listings:
        if os.path.exists(f"/home/josh/Projects/Job-Search/data/{listing.id}.txt"):
            with open(f"/home/josh/Projects/Job-Search/data/{listing.id}.txt", "r") as f:
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
            description = site.get_listing_description(listing.id)
            description_utf = description.encode("utf-8", "ignore").decode("utf-8", "ignore")
            try:
                with open(f"/home/josh/Projects/Job-Search/data/{listing.id}.txt", "w+") as f:
                    f.write(description_utf)
            except OSError as e:
                print(f"Error writing file for listing {listing.id}: {e}")
        except Exception as e:
            print(f"Error fetching description for listing {listing.id}: {e}")

    # for file in tqdm(os.listdir("/home/josh/Projects/Job-Search/data/")):
    #     file_id = file.split(".")[0]
    #     if not Listing.select().where(Listing.id == file_id).exists():
    #         try:
    #             os.remove(f"/home/josh/Projects/Job-Search/data/{file}")
    #         except OSError as e:
    #             print(f"Error deleting file {file}: {e}")


if __name__ == "__main__":
    main()
