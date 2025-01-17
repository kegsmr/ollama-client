import os

from flask import Flask, request, jsonify, render_template, send_from_directory
import ollama


app = Flask(__name__)

client = ollama.Client()

model = "llama2-uncensored"


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

	try:
		
		# Send message to Ollama and get the response
		response = client.generate(model=model, prompt=user_input)

		return jsonify({"reply": response.response})

	except Exception as e:

		return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
	app.run(debug=True)
