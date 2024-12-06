from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForCausalLM


def main():
    # pipe = pipeline("translation", model="google-t5/t5-small")
    # tokenizer = AutoTokenizer.from_pretrained("dslim/bert-base-NER")
    # model = AutoModelForTokenClassification.from_pretrained("dslim/bert-base-NER")

    with open("../job_descriptions/Full Stack Developer-Clicks IT Recruitment (QLD)-74177500.html") as f:
        desc = f.read()

    model_name = "Qwen/Qwen2.5-1.5B-Instruct"

    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="auto", device_map="auto")
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # prompt = "Give me a short introduction to large language model."
    messages = [
        {"role": "system", "content": "Please create a single sentence summary of this job description."},
        {"role": "user", "content": desc},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    generated_ids = model.generate(**model_inputs, max_new_tokens=512)
    generated_ids = [
        output_ids[len(input_ids) :] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]

    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    print(response)


if __name__ == "__main__":
    main()
