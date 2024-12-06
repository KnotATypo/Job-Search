import socket

from fabric import Connection
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM

from model import Listing
from util import is_server

model_name = "Qwen/Qwen2.5-1.5B-Instruct"
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="auto", device_map="auto")
tokenizer = AutoTokenizer.from_pretrained(model_name)


def main():
    listings = Listing.select().where(Listing.summary == "").execute()
    if is_server():
        for listing in tqdm(listings):
            with open(f"/home/josh/Job-Search/descriptions/{listing.id}.txt") as f:
                description = f.read()
                if description == "":
                    continue
                response = summary(str(description))
    else:
        with Connection("jobs.lan", "josh") as c, c.sftp() as sftp:
            for listing in tqdm(listings):
                with sftp.open(f"Job-Search/descriptions/{listing.id}.txt") as f:
                    description = f.read()
                    if description == "":
                        continue
                    response = summary(str(description))


# Please create a single sentence summary of this job description.


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
