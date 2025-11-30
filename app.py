from __future__ import annotations

import re
import os
import json
import random
from pprint import pprint
from datetime import datetime
from functools import lru_cache

import numpy
import ollama
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, render_template, \
    send_from_directory, session, abort

import models


app = Flask(__name__)
app.secret_key = os.urandom(24)

client = ollama.Client()


def format_response(response: str) -> str:

    response = response.replace("```\n", "```")
    response = response.replace("\n", " <br>")

    response = format_links(response)

    response = format_code_blocks(response)

    return response


def format_links(text: str) -> str:

    t = []
    c = False

    for word in text.split(" "):
        if "```" in word or "`" in word:
            c = not c
            t.append(word)
        else:    
            if not c and is_link(word):
                link = format_link(word)
                t.append(f"<a href='{link}' target='_blank'>{word}</a>")
            else:
                t.append(word)

    return " ".join(t)


def format_link(text: str) -> str:

    while text and text[-1] in [".", "!", ",", "?"]:
        text = text[:-1]

    if text.startswith("http://") or text.startswith("https://"):
        return text
    else:
        return f"http://{text}"


def format_code_blocks(text: str) -> str:

    # Function to replace code blocks with styled <div>
    def format_block_code(match):
        code = match.group(1)
        return '<div class="code-block" style="background-color: #f4f4f4; ' \
               'border: 1px solid #ddd; padding: 10px; margin: 10px 0; ' \
              f'font-family: monospace; white-space: pre-wrap;">{code}</div>'

    # Function to replace inline code with <code>
    def format_inline_code(match):
        code = match.group(1)
        return '<code style="background-color: #f4f4f4; padding: 2px 4px; ' \
              f'border-radius: 4px; font-family: monospace;">{code}</code>'

    # Format block code first
    formatted_text = re.sub(
        r'```(.*?)```', format_block_code, text, flags=re.S
    )

    # Format inline code
    formatted_text = re.sub(
        r'`([^`]+)`', format_inline_code, formatted_text
    )

    return formatted_text


def is_link(text: str) -> bool:

    while text and text[-1] in [".", "!", ",", "?"]:
        text = text[:-1]

    # Regular expression for detecting URLs
    url_regex = re.compile(
        r'^(https?:\/\/)?'  # Optional http or https scheme
        r'(www\.)?'         # Optional www subdomain
        r'[a-zA-Z0-9-]+'    # Domain name
        r'(\.[a-zA-Z]{2,})' # Top-level domain (e.g., .com, .org)
        r'(\/[^\s]*)?$'     # Optional path, query, or fragment
    )

    return bool(url_regex.match(text))


def html_to_text(html: str) -> str:

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Remove unwanted elements (e.g., script, style, etc.)
    for unwanted in soup(['script', 'style', 'head', 'meta', 'noscript']):
        unwanted.decompose()

    # Extract the visible text
    visible_text = soup.get_text(separator='\n').strip()

    t = []
    for line in visible_text.splitlines():
        if line:
            t.append(line.strip())

    return "\n".join(t)


@lru_cache(maxsize=10240)
def embed(text: str) -> numpy.ndarray:
    v = numpy.array(
        ollama.embeddings(
            model="nomic-embed-text",
            prompt=text
        )["embedding"],
        dtype=numpy.float32
    )
    return v / numpy.linalg.norm(v)


def embed_conversation(conversation: list[dict]):
    text = ""
    for message in conversation:
        role = (message.get('role') or '').strip()
        content = (message.get('content') or '').strip().replace('\n', ' ')
        if role and content:
            text += f"{role}: {content}\n"
    return embed(text.strip())


def cosine(a: numpy.ndarray, b: numpy.ndarray) -> float:
    return float(numpy.dot(a, b))


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
    challenge_directory = os.path.join(
        os.getcwd(), '.well-known', 'acme-challenge')
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
def chat(model: str, user_input=""):

    model = model.lower()

    if not user_input:
        user_input = request.json.get('message')

    messages = []

    # Session cookie message history storage
    session.setdefault(model, [])

    if user_input:

        # Limit the amount of messages stored
        session[model] = session[model][-100:]

        # Get default conversations from the model
        conversations = models.messages.get(model, [])

        # Shuffle and limit
        random.shuffle(conversations)
        conversations = conversations[:max(10, min(len(conversations) // 3, 1000))]

        # Sort by ascending cosine similarity
        conversations = sorted(
            conversations, 
            key=lambda conversation: sum([
                cosine(
                    embed(user_input),
                    embed_conversation(conversation)
                ),
                cosine(
                    embed_conversation(session[model]),
                    embed_conversation(conversation)
                )
            ])
        )

        # Limit the amount of conversations to include
        conversations = conversations[-30:]

        # Concatenate everything into one array
        for conversation in conversations:
            for message in conversation:
                messages.append(message)

        urls = []
        for word in user_input.split(" "):
            if is_link(word):
                urls.append(format_link(word))

        webpages = {}
        failed_urls = {}
        for url in urls:
            try:
                r = requests.get(url)
                if r.status_code == 200:
                    webpages[url] = html_to_text(r.text)
                else:
                    raise Exception(f"{r.status_code} error")
            except Exception as e:
                failed_urls[url] = e

        # Append the new user message to the history
        session[model].append(
            {
                "role": "user",
                "content": user_input
            }
        )

        for url, webpage in webpages.items():
            session[model].append({
                "role": "system",
                "content": f"Contents of '{url}':\n\n\"{webpage}\""
            })

        for url, error in failed_urls.items():
            session[model].append({
                "role": "system",
                "content": f"Failed to load {url}:\n\n\"{error}\""
            })

    else:

        session[model] = [
            {
                "role": "user",
                "content": "Who are you?"
            }
        ]

    try:

        # Send the entire prompt to Ollama and get the response
        response = client.chat(
            model=model,
            messages=(messages + session[model])
        ).message.content.strip()

        # Append the bot's response to the history
        session[model].append({
            "role": "assistant",
            "content": response,
        })

        response = format_response(response)

        return jsonify({"reply": response})

    except Exception as e:

        return jsonify({"error": str(e)}), 500


@app.route('/<model>/like', methods=['POST'])
def like(model: str):

    model = model.lower()

    user_messages = []
    bot_messages = []
    for message in session[model]:
        if message["role"] == "user":
            user_messages.append(message)
        elif message["role"] == "assistant":
            bot_messages.append(message)

    user_message = user_messages[-1]
    bot_message = bot_messages[-1]

    data = [
        user_message,
        bot_message
    ]

    # Just so you dont have to restart the program
    models.messages.setdefault(model, [])
    models.messages[model].append(data)

    # Ensure the 'liked' directory structure exists
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    directory = os.path.join("liked", model)
    os.makedirs(directory, exist_ok=True)

    # File path
    file_path = os.path.join(directory, f"{timestamp}.json")

    # Write the JSON data to the file
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

    # If no errrors occur
    return jsonify(["SUCCESS"])


@app.route('/<model>/dislike', methods=['POST'])
def dislike(model: str):

    model = model.lower()

    # Remove the unwanted response
    message = session[model].pop(-1)

    # Remove the last user message and all messages after
    while message["role"] != "user":
        message = session[model].pop(-1)
    content = message["content"]

    # Redo the chat with the last user message
    return chat(model, content)


if __name__ == '__main__':
    app.run(debug=True)
