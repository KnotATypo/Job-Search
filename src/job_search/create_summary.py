import os

from dotenv import load_dotenv
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM

from job_search.model import Listing, JobToListing

load_dotenv()

model_name = os.getenv("SUMMARY_MODEL_NAME")
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="auto", device_map="auto")
tokenizer = AutoTokenizer.from_pretrained(model_name)


def main():
    listings = Listing.select(Listing, JobToListing).join(JobToListing).execute()
    for l in [l for l in listings if (l.jobtolisting.job_id.status == "blacklist") and l.summary == ""]:
        l.summary = "blacklist"
        l.save()
    listings = [l for l in listings if (l.jobtolisting.job_id.status in ["new", "interested"]) and l.summary == ""]
    for listing in tqdm(listings):
        try:
            with open(f"{os.getenv("DATA_DIRECTORY")}/{listing.id}.txt") as f:
                summarise_and_save(f.read(), listing)
        except FileNotFoundError as e:
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
