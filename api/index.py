import os
import tempfile
from http import HTTPStatus
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Get API key from environment
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

def process_image(file_path):
    """Process an image file and return VQA result."""
    # For now, return a simple response
    # The full implementation would go here
    return {"answer": "Image processing endpoint is working. Full implementation pending."}

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

# For local testing
if __name__ == '__main__':
    app.run(debug=True)
