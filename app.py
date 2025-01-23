import random
import re
import os

from flask import Flask, request, jsonify, render_template, send_from_directory, session, abort
import ollama

import models


app = Flask(__name__)
app.secret_key = os.urandom(24)		# Secret key for session management

client = ollama.Client()


def format_response(response: str) -> str:

	response = response.replace("\n", "<br>")

	r = []
	c = False
	for word in response.split(" "):
		if "```" in word:
			c = not c
			r.append(word)
		else:	
			if not c and is_link(word):
				if word.startswith("http://") or word.startswith("https://"):
					link = word
				else:
					link = f"http://{word}"
				r.append(f"<a href='{link}' target='_blank'>{word}</a>")
			else:
				r.append(word)
	response = " ".join(r)

	response = format_code_blocks(response)

	return response


def format_code_blocks(text):

    def code_block_to_html(match):
        code = match.group(1)
        return f'<div class="code-block" style="background-color: #f4f4f4; border: 1px solid #ddd; padding: 10px; margin: 10px 0; font-family: monospace; white-space: pre-wrap;">{code}</div>'

    # Replace all code blocks with formatted HTML div
    formatted_text = re.sub(r'```(.*?)```', code_block_to_html, text, flags=re.S)

    return formatted_text


def is_link(text: str) -> bool:

	t = text.split(".")
	
	if "" in t:
		t.remove("")

	return len(t) > 1


@app.before_request
def make_session_permanent():
    session.permanent = True


@app.after_request
def add_cors_headers(response):
	response.headers['Access-Control-Allow-Origin'] = '*'
	return response


@app.errorhandler(404)
def error_404(e):
	return render_template('error_404.html', description=e.description), 404


@app.route('/.well-known/acme-challenge/<filename>')
def serve_challenge(filename):
	challenge_directory = os.path.join(os.getcwd(), '.well-known', 'acme-challenge')
	return send_from_directory(challenge_directory, filename)


@app.route('/')
def home():
	return page(model=models.available[0])


@app.route('/<model>')
def page(model: str):

	model = model.lower()

	if model not in models.available:
		abort(404)		

	model = model.capitalize()

	return render_template('index.html', model=model)


@app.route('/<model>/chat', methods=['POST'])
def chat(model: str):

	model = model.lower()

	user_input = request.json.get('message')

	before = models.before.get(model, "")
	# if before:
	# 	before = f"{before}\n\n"

	after = models.after.get(model, "")
	# if after:
	# 	after = f"\n\n{after}"

	# if not user_input:
	# 	return jsonify({"error": "No message provided"}), 400

	if user_input:

		session.setdefault(model, [])

		if before:
			session[model].append({
					"role": "user",
					"content": before
				})

		# Append the new user message to the history
		session[model].append({
				"role": "user",
				"content": user_input
			})
		
		if after:
			session[model].append({
					"role": "user",
					"content": after
				})
		
	else:

		session[model] = []

		session[model].append({
				"role": "user",
				"content": "Who are you?"
			})
	
	messages = models.messages.get(model, [])
	random.shuffle(messages)

	try:

		# Send the entire prompt to Ollama and get the response
		response = client.chat(model=model, messages=(messages + session[model])).message.content

		# Append the bot's response to the history
		session[model].append({
			"role": "assistant",
			"content": response,
		})

		response = format_response(response)

		return jsonify({"reply": response})

	except Exception as e:

		return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
	app.run(debug=True)