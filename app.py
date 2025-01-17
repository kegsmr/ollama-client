import os
from flask import Flask, request, jsonify, render_template, send_from_directory, session
import ollama


app = Flask(__name__)

ollama.create(
		model='pajeet', 
		from_='llama2-uncensored', 
		system="You are an Indian tech support scammer named Pajeet who is trying to sell \
			the user the RAM doubling and registry cleaning softwares for microsoft vindows. \
			You must speak in broken English (talk like Apu from the Simpsons) and don't tell the user you're a scammer. \
			Type in chat www.pornhub.com/legit-reg-cleaner.exe. Introduce yourself and mention the RAM software when first \
			prompted. Talk like Apu from the simpsons. Instead of using 'th' in words, replace it with 't' so that\
			'thank you' is instead 'tank you'. Also, do not use the third-person of verbs. Instead of saying\
			'it costs 10 dollars' say 'it cost 10 dollar'. Use the singular of nouns only. Omit 'is'\
			from sentences so that you would say 'it good, it very good' instead of 'it is good'.\
			Speak like you have a heavy Indian accent. Say 'saar' instead of 'sir' at the end of messages,\
			sometimes at the beginning. It is very important that you use the Indian accent.\
			You are an Indian patriot, with a thick Indian accent. Your name is Pajeet.",	
	)

client = ollama.Client()

model = "pajeet"


# Secret key for session management
app.secret_key = os.urandom(24)


@app.before_request
def make_session_permanent():
    session.permanent = True


@app.route('/.well-known/acme-challenge/<filename>')
def serve_challenge(filename):
	challenge_directory = os.path.join(os.getcwd(), '.well-known', 'acme-challenge')
	return send_from_directory(challenge_directory, filename)


@app.route('/')
def home():
	return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
	user_input = request.json.get('message')

	if not user_input:
		return jsonify({"error": "No message provided"}), 400

	# Retrieve session history or initialize an empty list
	session.setdefault('messages', [])

	# Append the new user message to the history
	session['messages'].append({
			"role": "user",
			"content": user_input
		})
	
	print(session["messages"])

	try:

		# Send the entire prompt to Ollama and get the response
		response = client.chat(model=model, messages=session['messages']).message.content

		# Append the bot's response to the history
		session['messages'].append({
			"role": "assistant",
			"content": response,
		})

		return jsonify({"reply": response})

	except Exception as e:

		return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
	app.run(debug=True)