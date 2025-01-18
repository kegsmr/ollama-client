import os

import ollama


BASE_MODEL = 'llama2-uncensored'


available = []


def create(model: str, *args, **kwargs):

	model = model.lower()

	available.append(model)

	return ollama.create(model=model, *args, **kwargs)


create(model='assistant', from_=BASE_MODEL)

os.makedirs("models", exist_ok=True)

for filename in os.listdir("models"):

	model = ".".join(filename.split(".")[:-1]).lower()
	system = open(os.path.join("models", filename), "r").read()

	create(model=model, from_=BASE_MODEL, system=system)