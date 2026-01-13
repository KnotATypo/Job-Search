import os

import psycopg2
from dotenv import load_dotenv
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM

from job_search import util
from job_search.model import Listing

load_dotenv()

model_name = os.getenv("SUMMARY_MODEL_NAME")
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="auto", device_map="auto")
tokenizer = AutoTokenizer.from_pretrained(model_name)


def main():
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
        FROM jobtolisting
                 JOIN public.job j ON j.id = jobtolisting.job_id
                 JOIN public.listing l ON l.id = jobtolisting.listing_id
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
    for listing in tqdm(need_summary):
        try:
            with open(util.description_path(listing)) as f:
                summarise_and_save(f.read(), listing)
        except FileNotFoundError as e:
            # This will fail if the listing has been archived, but jobs old enough to be archived are no longer relevant
            print(f"File for listing {listing.id} not found: {e}")
            summarise_and_save("", listing)


def summarise_and_save(description: str, listing: Listing):
    if description == "" or description == b"":
        response = "N/A"
    else:
        response = summary(str(description))
        if "!!!!!!" in response:
            response = summary(str(description))
    listing.summary = response
    listing.save()


def summary(description):
    messages = [
        {
            "role": "system",
            "content": "Please create a single sentence summary of this job description without any corporate fluff",
        },
        {"role": "user", "content": description},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
    generated_ids = model.generate(**model_inputs, max_new_tokens=512)
    generated_ids = [
        output_ids[len(input_ids) :] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return response


if __name__ == "__main__":
    main()
