import os

import ollama


BASE_MODEL = 'llama2-uncensored'


available = []

messages = {}


def create(model: str, *args, **kwargs):

	model = model.lower()

	available.append(model)

	return ollama.create(model=model, *args, **kwargs)


def model_name_from_filename(filename: str) -> str:

	return ".".join(filename.split(".")[:-1]).lower()


create(model='assistant', from_=BASE_MODEL)


for directory in ["prompts", "messages"]:

	os.makedirs(directory, exist_ok=True)


for filename in os.listdir("prompts"):

	model = model_name_from_filename(filename)
	system = open(os.path.join("prompts", filename), "r", encoding="utf-8").read()

	create(model=model, from_=BASE_MODEL, system=system)


for filename in os.listdir("messages"):

	model = model_name_from_filename(filename)
	
	m = []

	with open(os.path.join("messages", filename), "r", encoding="utf-8") as file:
		for line in file:
			l = line.strip()
			if len(l) > 0:
				m.append({
					"role": "assistant",
					"content": l,
				})

	messages[model] = m