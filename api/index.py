import json
import os
import base64
import tempfile
from http import HTTPStatus
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

def process_image(file_content):
    # This is a placeholder - the actual processing will be done in the main app
    # We'll move the relevant code here in the next step
    return {"answer": "This is a test response. Image processing will be implemented here."}

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), HTTPStatus.BAD_REQUEST
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), HTTPStatus.BAD_REQUEST
    
    try:
        # Save the file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.save(temp_file.name)
            # Process the image
            result = process_image(temp_file.name)
            return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    finally:
        # Clean up the temporary file
        if 'temp_file' in locals() and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

# This is the Vercel serverless function entry point
def handler(event, context):
    # This will be called by Vercel
    from werkzeug.serving import run_simple
    from werkzeug.wrappers import Request, Response
    
    # Convert Vercel event to WSGI environment
    environ = event.get('__wsgi_environ', {})
    request = Request(environ)
    
    # Handle the request with Flask
    with app.request_context(environ):
        response = app.full_dispatch_request()
    
    # Convert Flask response to Vercel format
    return {
        'statusCode': response.status_code,
        'headers': dict(response.headers),
        'body': response.get_data(as_text=True)
    }

# For local testing
if __name__ == '__main__':
    app.run(debug=True)
