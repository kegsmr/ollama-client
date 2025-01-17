import os
from flask import Flask, request, jsonify, render_template, send_from_directory, session, abort
import ollama

import models


app = Flask(__name__)
app.secret_key = os.urandom(24)		# Secret key for session management

client = ollama.Client()


@app.before_request
def make_session_permanent():
    session.permanent = True


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

	# if not user_input:
	# 	return jsonify({"error": "No message provided"}), 400

	# Retrieve session history or initialize an empty list
	session.setdefault(model, [])

	if user_input:

		# Append the new user message to the history
		session[model].append({
				"role": "user",
				"content": user_input
			})
		
	else:

		session[model].append({
				"role": "user",
				"content": "Hello!"
			})
	
	#print(session[model])

	try:

		# Send the entire prompt to Ollama and get the response
		response = client.chat(model=model, messages=session[model]).message.content

		# Append the bot's response to the history
		session[model].append({
			"role": "assistant",
			"content": response,
		})

		return jsonify({"reply": response})

	except Exception as e:

		return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
	app.run(debug=True)