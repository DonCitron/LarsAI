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
    """Enhanced web search with better query generation and result filtering."""
    try:
        # Extract key terms and concepts for better search
        search_queries = []
        
        # Primary query
        search_queries.append(query)
        
        # Add domain-specific terms if detected
        if any(term in query.lower() for term in ['sap', 'erp', 'abap', 'fiori', 'hana', 's/4hana', 'ariba', 'successfactors', 'concur']):
            # SAP-specific search queries
            search_queries.append(f"{query} SAP help documentation")
            search_queries.append(f"{query} SAP community wiki")
            if any(module in query.lower() for module in ['sd', 'sales', 'distribution']):
                search_queries.append(f"{query} SAP SD sales distribution")
            elif any(module in query.lower() for module in ['mm', 'materials', 'procurement']):
                search_queries.append(f"{query} SAP MM materials management")
            elif any(module in query.lower() for module in ['fi', 'finance', 'accounting']):
                search_queries.append(f"{query} SAP FI financial accounting")
            elif any(module in query.lower() for module in ['co', 'controlling']):
                search_queries.append(f"{query} SAP CO controlling")
            elif any(module in query.lower() for module in ['hr', 'human', 'payroll']):
                search_queries.append(f"{query} SAP HR human resources")
            elif any(module in query.lower() for module in ['pp', 'production', 'planning']):
                search_queries.append(f"{query} SAP PP production planning")
        elif any(term in query.lower() for term in ['calculate', 'equation', 'formula']):
            search_queries.append(f"{query} math formula solution")
        elif any(term in query.lower() for term in ['history', 'war', 'century', 'year']):
            search_queries.append(f"{query} historical facts")
        elif any(term in query.lower() for term in ['biology', 'cell', 'organism', 'DNA']):
            search_queries.append(f"{query} biology science")
        elif any(term in query.lower() for term in ['chemistry', 'element', 'reaction', 'molecule']):
            search_queries.append(f"{query} chemistry science")
        elif any(term in query.lower() for term in ['physics', 'force', 'energy', 'mass']):
            search_queries.append(f"{query} physics science")
        
        all_results = []
        
        with DDGS() as ddgs:
            for search_query in search_queries[:2]:  # Limit to 2 queries to avoid rate limiting
                try:
                    results = list(ddgs.text(search_query, max_results=max_results))
                    # Filter and score results
                    filtered_results = []
                    for result in results:
                        # Skip low-quality sources
                        if any(domain in result.get('href', '').lower() for domain in ['yahoo.com', 'answers.com']):
                            continue
                        # Prefer educational and authoritative sources
                        if any(domain in result.get('href', '').lower() for domain in ['sap.com', 'help.sap.com', 'community.sap.com', 'blogs.sap.com', 'sapinsider.org']):
                            result['authority_score'] = 1.0  # SAP official sources
                        elif any(domain in result.get('href', '').lower() for domain in ['.edu', 'wikipedia', 'britannica', 'khan']):
                            result['authority_score'] = 0.9  # Educational sources
                        elif any(domain in result.get('href', '').lower() for domain in ['sapcenter.com', 'sapgenie.com', 'guru99.com']):
                            result['authority_score'] = 0.8  # SAP training sources
                        else:
                            result['authority_score'] = 0.5
                        filtered_results.append(result)
                    
                    all_results.extend(filtered_results)
                except Exception as inner_e:
                    print(f"Error in individual search query '{search_query}': {inner_e}")
                    continue
        
        # Remove duplicates and sort by authority
        seen_urls = set()
        unique_results = []
        for result in all_results:
            url = result.get('href', '')
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        # Sort by authority score and return top results
        unique_results.sort(key=lambda x: x.get('authority_score', 0), reverse=True)
        return unique_results[:max_results]
        
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

        # Extract text from the image with enhanced OCR
        initial_prompt = """Carefully analyze the image and extract the following information with high precision:
        
        IMPORTANT: Pay close attention to text clarity, formatting, and context.
        
        Extract:
        1. The complete question text (including any sub-questions or context)
        2. ALL multiple-choice options with their labels (A, B, C, D, etc.)
        3. Number of required answers (look for phrases like "Select 2 answers", "Choose 3 options", "Kreuzen Sie 2 Antworten an", "Mark all that apply", etc.)
        4. Any additional context or instructions
        
        Text preprocessing guidelines:
        - Clean up OCR artifacts and formatting issues
        - Preserve mathematical symbols, equations, and special characters
        - Maintain proper spacing and punctuation
        - Handle multiple languages appropriately
        
        Return the information in this JSON format:
        {
            "question": "the complete question text",
            "options": ["option A text", "option B text", "option C text"],
            "answers_required": 1,
            "additional_context": "any extra instructions or context",
            "language": "detected language (en, de, etc.)"
        }
        
        If the number of required answers is not specified, set answers_required to 1."""
        
        # First API call to extract question and options
        initial_payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1500,
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
        
        # Prepare answer prompt with number of required answers
        answers_required = question_data.get("answers_required", 1)
        
        # Second API call with SAP-enhanced reasoning
        answer_prompt = f"""Using the question, options, and web search results (if available), 
        analyze ALL the given options using structured SAP expertise and reasoning.
        
        IMPORTANT: The question requires selecting {answers_required} correct answer(s).
        
        Step-by-step SAP analysis process:
        1. DOMAIN IDENTIFICATION: Identify if this is SAP-related and which SAP domain/module
        2. SAP CONTEXT ANALYSIS: Consider:
           - SAP module-specific functionality (SD, MM, FI, CO, HR, PP, etc.)
           - SAP technical aspects (ABAP, HANA, Fiori, S/4HANA, etc.)
           - SAP business processes and best practices
           - SAP certification knowledge and common exam patterns
        3. OPTION EVALUATION: For each option, analyze:
           - Technical accuracy based on SAP functionality
           - Business process alignment with SAP best practices
           - Common SAP terminology and concepts
           - Typical SAP certification question patterns
           - Integration with other SAP modules
        4. CONFIDENCE CALIBRATION: Base confidence on:
           - Accuracy of SAP technical knowledge
           - Alignment with SAP business processes
           - Quality of web search evidence from SAP sources
           - Consistency with SAP certification standards
        
        For NON-SAP questions, use general domain expertise as before.
        
        Return a JSON object with this format:
        {{
            "domain": "SAP [Module] or [General Subject]",
            "sap_module": "SD/MM/FI/CO/HR/PP/Technical/Cloud/etc. or null if not SAP",
            "key_concepts": ["concept1", "concept2"],
            "answers_required": {answers_required},
            "ranked_answers": [
                {{"text": "option text", "confidence": 0.85, "rank": 1, "is_recommended": true, "reasoning": "SAP-specific detailed explanation"}},
                {{"text": "option text", "confidence": 0.60, "rank": 2, "is_recommended": true, "reasoning": "SAP-specific detailed explanation"}},
                {{"text": "option text", "confidence": 0.30, "rank": 3, "is_recommended": false, "reasoning": "SAP-specific detailed explanation"}},
                ...
            ],
            "overall_confidence": 0.75,
            "sap_notes": "Additional SAP-specific insights or common pitfalls"
        }}
        
        Set "is_recommended": true for the top {answers_required} answers you recommend selecting.
        Include ALL options with detailed SAP-specific reasoning for each.
        For SAP questions, reference specific transaction codes, tables, or processes when relevant."""
        
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1000,
            "system": """You are an expert SAP consultant and certified trainer who specializes in analyzing multiple-choice questions across all SAP domains. You have deep knowledge of:

SAP ERP MODULES:
- SD (Sales & Distribution): Order-to-Cash, Pricing, Shipping, Billing
- MM (Materials Management): Procurement-to-Pay, Inventory, Vendor Management  
- FI (Financial Accounting): General Ledger, Accounts Payable/Receivable, Asset Accounting
- CO (Controlling): Cost Centers, Profit Centers, Internal Orders, Profitability Analysis
- HR/HCM (Human Capital Management): Personnel, Payroll, Time Management, Organizational Management
- PP (Production Planning): MRP, Capacity Planning, Shop Floor Control
- QM (Quality Management): Quality Planning, Inspection, Certificates
- PM (Plant Maintenance): Preventive/Corrective Maintenance, Work Orders

SAP TECHNOLOGIES:
- ABAP Programming, Workbench, Data Dictionary, SmartForms, Adobe Forms
- SAP HANA: In-Memory Computing, Modeling, SQL Script
- SAP Fiori/UI5: User Experience, Launchpad, OData Services
- SAP S/4HANA: Simplification, Universal Journal, Embedded Analytics
- SAP BW/BI: Data Warehousing, InfoCubes, Queries, Reports
- SAP PI/PO: Integration, Mapping, Adapters, Monitoring

SAP CLOUD SOLUTIONS:
- SuccessFactors: Talent Management, Employee Central, Performance
- Ariba: Procurement, Sourcing, Supplier Management
- Concur: Travel & Expense Management
- SAP Cloud Platform: Integration, Development, Analytics

BUSINESS PROCESSES & BEST PRACTICES:
- Order-to-Cash, Procure-to-Pay, Record-to-Report
- Master Data Management, Configuration vs Customization
- Authorization Concepts, Transport Management
- Integration scenarios, Interface technologies""",
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
        
        # Make the second API call to get the ranked answers
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        # Extract and parse the ranked answers
        response_text = response.json()["content"][0]["text"].strip()
        
        # Debug logging
        print(f"Raw API response: {response_text}")
        
        try:
            # Try to extract JSON from the response if it's wrapped in markdown
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            
            result = json.loads(response_text)
            print(f"Parsed JSON result: {result}")
            
            # Ensure backward compatibility
            if "ranked_answers" in result:
                return jsonify({
                    "answers": result["ranked_answers"],
                    "answers_required": result.get("answers_required", 1)
                })
            elif "answers" in result and isinstance(result["answers"], list):
                return jsonify({
                    "answers": result["answers"],
                    "answers_required": result.get("answers_required", 1)
                })
            else:
                # Handle old format or single answer
                return jsonify({"answers": [{"text": response_text, "confidence": 1.0, "rank": 1, "is_recommended": True}]})
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Failed to parse: {response_text}")
            # Fallback to single answer format if parsing fails
            return jsonify({
                "answers": [{"text": response_text, "confidence": 1.0, "rank": 1, "is_recommended": True}],
                "answers_required": 1
            })
        
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
            "model": "claude-3-5-sonnet-20241022",
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
        
        # Prepare answer prompt with number of required answers
        answers_required = question_data.get("answers_required", 1)
        
        # Second API call to determine possible answers with confidence scores
        answer_prompt = f"""Using the question, options, and web search results (if available), 
        analyze ALL the given options and rank them by likelihood of being correct.
        
        IMPORTANT: The question requires selecting {answers_required} correct answer(s).
        
        Return a JSON object with this format:
        {{
            "answers_required": {answers_required},
            "ranked_answers": [
                {{"text": "option text", "confidence": 0.85, "rank": 1, "is_recommended": true}},
                {{"text": "option text", "confidence": 0.60, "rank": 2, "is_recommended": true}},
                {{"text": "option text", "confidence": 0.30, "rank": 3, "is_recommended": false}},
                ...
            ]
        }}
        
        Set "is_recommended": true for the top {answers_required} answers you recommend selecting.
        Include ALL options in your response, even those with low confidence.
        Base your confidence on the evidence from web search results and your knowledge."""
        
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 500,
            "system": "You are a helpful assistant that analyzes multiple-choice questions and provides confidence scores for all options.",
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
        
        # Extract and parse the ranked answers
        response_text = response.json()["content"][0]["text"].strip()
        
        # Debug logging
        print(f"Raw API response: {response_text}", file=sys.stderr)
        
        try:
            # Try to extract JSON from the response if it's wrapped in markdown
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                if end != -1:
                    response_text = response_text[start:end].strip()
            
            result = json.loads(response_text)
            print(f"Parsed JSON result: {result}", file=sys.stderr)
            
            # Ensure consistent format
            if "ranked_answers" in result:
                return {
                    "answers": result["ranked_answers"],
                    "answers_required": result.get("answers_required", 1)
                }
            elif "answers" in result and isinstance(result["answers"], list):
                return {
                    "answers": result["answers"],
                    "answers_required": result.get("answers_required", 1)
                }
            else:
                # Handle old format or single answer
                return {
                    "answers": [{"text": response_text, "confidence": 1.0, "rank": 1, "is_recommended": True}],
                    "answers_required": 1
                }
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}", file=sys.stderr)
            print(f"Failed to parse: {response_text}", file=sys.stderr)
            # Fallback to single answer format if parsing fails
            return {
                "answers": [{"text": response_text, "confidence": 1.0, "rank": 1, "is_recommended": True}],
                "answers_required": 1
            }
        
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
