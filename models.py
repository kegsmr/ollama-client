import os
import json

import ollama


BASE_MODEL = 'llama2-uncensored'


available = []

messages = {}
after = {}
before = {}


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

	if filename.endswith(".txt"):

		model = model_name_from_filename(filename)
		system = open(os.path.join("prompts", filename), "r", encoding="utf-8").read()

		create(model=model, from_=BASE_MODEL, system=system)


for filename in os.listdir("messages"):

	if filename.endswith(".txt"):

		model = model_name_from_filename(filename)
		
		m = []

		with open(os.path.join("messages", filename), "r", encoding="utf-8") as file:
			for line in file:
				l = line.strip()
				if len(l) > 0:
					role = "assistant"
					if l.startswith("assistant: ") or l.lower().startswith(f"{model}: "):
						content = l.split(": ", 1)[1]
					elif l.startswith("user: ") or l.startswith("You: "):
						content = l.split(": ", 1)[1]
						role = "user"
					else:
						content = l
					message = {
						"role": role,
						"content": content,
					}
					if len(m) == 0 or not (m[-1][-1]["role"] == "user" and role == "assistant"):
						m.append([message])
					else:
						m[-1].append(message)

		messages[model] = m


for model in os.listdir("liked"):

	path = os.path.join("liked", model)

	for filename in os.listdir(path):

		messages[model].append(json.load(open(os.path.join(path, filename), "r", encoding="utf-8")))
		print(messages[model])


# for filename in os.listdir("after"):

# 	if filename.endswith(".txt"):

# 		model = model_name_from_filename(filename)
# 		a = open(os.path.join("after", filename), "r", encoding="utf-8").read()

# 		after[model] = a


# for filename in os.listdir("before"):

# 	if filename.endswith(".txt"):

# 		model = model_name_from_filename(filename)
# 		b = open(os.path.join("before", filename), "r", encoding="utf-8").read()

# 		before[model] = b