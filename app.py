import os
import base64
import json
import requests
import sys
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

def search_web(query, max_results=3):
    """Search the web for information related to the query."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return results
    except Exception as e:
        print(f"Error during web search: {e}")
        return []

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)  # Enable CORS for all routes

# Load API key from environment variables
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file found"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not ANTHROPIC_API_KEY:
        return jsonify({"error": "Anthropic API key not set!"}), 500

    try:
        # Encode the image for the API
        base64_image = encode_image(file)

        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "anthropic-beta": "messages-2023-12-15"
        }

        # Extract text from the image
        initial_prompt = """Analyze the image and extract the following information:
        1. The question being asked
        2. All multiple-choice options (A, B, C, etc.)
        
        Return the information in this JSON format:
        {
            "question": "the question text",
            "options": ["option A", "option B", "option C"]
        }"""
        
        # First API call to extract question and options
        initial_payload = {
            "model": "claude-3-opus-20240229",
            "max_tokens": 1000,
            "system": "You are a helpful assistant that extracts questions and options from images.",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": initial_prompt
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_image
                            }
                        }
                    ]
                }
            ]
        }
        
        initial_response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=initial_payload
        )
        initial_response.raise_for_status()
        question_data = json.loads(initial_response.json()["content"][0]["text"])
        
        # Perform web search based on the question
        search_query = question_data["question"]
        search_results = search_web(search_query)
        
        # Prepare context for the second API call
        context = "Question: " + question_data["question"] + "\nOptions:\n"
        for i, option in enumerate(question_data["options"], 1):
            context += f"{i}. {option}\n"
            
        if search_results:
            context += "\nWeb search results:\n"
            for i, result in enumerate(search_results[:3], 1):
                context += f"{i}. {result['title']}: {result['body']}\n"
        
        # Second API call to determine the answer with web context
        answer_prompt = """Using the question, options, and web search results (if available), 
        determine the most likely correct answer. Return ONLY the text of the correct answer option, 
        without any explanations or introductory sentences. If you're not sure, make your best guess."""
        
        payload = {
            "model": "claude-3-opus-20240229",
            "max_tokens": 100,
            "system": "You are a helpful assistant that answers multiple-choice questions based on the given context.",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{context}\n\n{answer_prompt}"
                        }
                    ]
                }
            ]
        }
        
        # Make the second API call to get the answer
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        # Extract and return the answer
        answer = response.json()["content"][0]["text"].strip()
        return jsonify({"answer": answer})
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API request failed: {str(e)}"}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse API response"}), 500
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

# Serve static files
@app.route('/<path:path>')
def serve_static(path):
    return app.send_static_file(path)

def process_image(image_path):
    """Process an image file and return the result."""
    try:
        with open(image_path, 'rb') as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')
        
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "anthropic-beta": "messages-2023-12-15"
        }
        
        # First API call to extract question and options
        initial_prompt = """Analyze the image and extract the following information:
        1. The question being asked
        2. All multiple-choice options (A, B, C, etc.)
        
        Return the information in this JSON format:
        {
            "question": "the question text",
            "options": ["option A", "option B", "option C"]
        }"""
        
        initial_payload = {
            "model": "claude-3-opus-20240229",
            "max_tokens": 1000,
            "system": "You are a helpful assistant that extracts questions and options from images.",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": initial_prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_image
                            }
                        }
                    ]
                }
            ]
        }
        
        initial_response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=initial_payload
        )
        initial_response.raise_for_status()
        question_data = json.loads(initial_response.json()["content"][0]["text"])
        
        # Perform web search based on the question
        search_query = question_data["question"]
        search_results = search_web(search_query)
        
        # Prepare context for the second API call
        context = "Question: " + question_data["question"] + "\nOptions:\n"
        for i, option in enumerate(question_data["options"], 1):
            context += f"{i}. {option}\n"
            
        if search_results:
            context += "\nWeb search results:\n"
            for i, result in enumerate(search_results[:3], 1):
                context += f"{i}. {result['title']}: {result['body']}\n"
        
        # Second API call to determine the answer with web context
        answer_prompt = """Using the question, options, and web search results (if available), 
        determine the most likely correct answer. Return ONLY the text of the correct answer option, 
        without any explanations or introductory sentences. If you're not sure, make your best guess."""
        
        payload = {
            "model": "claude-3-opus-20240229",
            "max_tokens": 100,
            "system": "You are a helpful assistant that answers multiple-choice questions based on the given context.",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{context}\n\n{answer_prompt}"}
                    ]
                }
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        answer = response.json()["content"][0]["text"].strip()
        return {"answer": answer}
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Command-line mode for Netlify function
        image_path = sys.argv[1]
        result = process_image(image_path)
        print(json.dumps(result))
    else:
        # Start the server - Railway uses PORT environment variable
        port = int(os.environ.get('PORT', 5001))
        app.run(host='0.0.0.0', port=port, debug=False)
