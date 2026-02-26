import os

import psycopg2
from dotenv import load_dotenv
from ollama import Client
from tqdm import tqdm

from job_search.logger import logger, progress_bars
from job_search.model import Listing
from job_search.util import storage

load_dotenv()

# Connect to ollama and ensure the requested model is available
client = Client(host=os.getenv("OLLAMA_HOST"))
model_name = os.getenv("SUMMARY_MODEL_NAME")
if model_name not in [m.model for m in client.list().models]:
    logger.error(f"Model {model_name} not found")
    exit(1)

SUMMARY_PROMPT = os.getenv("SUMMARY_PROMPT")


def create_summary():
    connection = psycopg2.connect(
        host=os.getenv("DATABASE_HOST"),
        database=os.getenv("DATABASE_NAME"),
        user=os.getenv("DATABASE_USER"),
        password=os.getenv("DATABASE_PASSWORD"),
    )
    cursor = connection.cursor()
    # Get each listing with their summary and a pipe separated list of associated job statuses
    cursor.execute(
        """
        SELECT l.id, summary, STRING_AGG(status, '|')
        FROM listing l
                 JOIN public.job j ON j.id = l.job_id
        GROUP BY l.id
        """
    )
    need_blacklist = []
    need_summary = []
    for listing in cursor.fetchall():
        has_blacklist = [x == "blacklist" for x in listing[2].split("|")]
        if all(has_blacklist):
            if listing[1] != "blacklist":
                # Listings with only blacklist status jobs and without the "blacklist" summary
                need_blacklist.append(listing[0])
        elif any(has_blacklist) and listing[1] == "blacklist":
            # Listings that have previously been given the "blacklist" summary, but now have an associated job that isn't blacklisted
            need_summary.append(listing[0])
        elif listing[1] in ["", "N/A"] and any(x in ["new", "interested"] for x in listing[2].split("|")):
            # Remaining jobs without summaries that are still relevant to users
            need_summary.append(listing[0])
    connection.close()

    need_blacklist = Listing.select().where(Listing.id << need_blacklist)
    for l in need_blacklist:
        l.summary = "blacklist"
        l.save()

    need_summary = Listing.select().where(Listing.id << need_summary)
    # Remove any listings that we don't have a description for
    need_summary = [listing for listing in need_summary if storage.description_download(listing.id)]
    for listing in tqdm(need_summary, disable=not progress_bars):
        summarise_and_save(listing)
        logger.info(f"Summary saved for listing {listing.id}")


def summarise_and_save(listing: Listing):
    try:
        description = storage.read_description(listing.id)
        if description != "":
            response = summary(str(description))
        else:
            response = "N/A"
    except Exception as e:
        logger.warn(f"Error in creating summary for {listing.id}: {type(e).__name__} - {e}")
        response = "N/A"

    listing.summary = response
    listing.save()


def summary(description):
    response = client.chat(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": SUMMARY_PROMPT,
            },
            {"role": "user", "content": description},
        ],
    )

    return response.message.content


if __name__ == "__main__":
    create_summary()
