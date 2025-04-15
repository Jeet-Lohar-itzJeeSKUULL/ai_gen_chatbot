from pyexpat import model
from click import prompt
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
import base64
import time
from google.cloud import storage  # For Google Cloud Storage

# Initialize Flask app
app = Flask(__name__)

# --- SECURITY WARNING! ---
# Embedding your API key directly in the code is a SECURITY RISK.
# DO NOT do this for production applications or if you intend to share this code.
# Use environment variables or a secure configuration management system instead.
GOOGLE_API_KEY = "AIzaSyB_DWonK9u9o5xUzeXucE7xUMVAWaOh-w4"  # Replace with your actual Gemini API key
# --- END SECURITY WARNING! ---

# Configure Google Cloud Storage (replace with your credentials)
GCS_PROJECT_ID = "gen-lang-client-0350017142"
GCS_BUCKET_NAME = "jeeskuull"
# Ensure you have set up authentication for Google Cloud in your environment
# (e.g., using a service account key file and GOOGLE_APPLICATION_CREDENTIALS env var)
storage_client = storage.Client(project=GCS_PROJECT_ID)
bucket = storage_client.bucket(GCS_BUCKET_NAME)

# --- Helper Functions ---

def generate_image_prompt(description):
    prompt = f"Generate a digital painting of a game character who is {description}. Focus on visual details, including clothing style, hair, eyes, and overall personality conveyed through their appearance and pose. Ensure the image is suitable for use as a game character concept art."
    return prompt

def generate_image_with_gemini(prompt):
    if GOOGLE_API_KEY == "YOUR_ACTUAL_GEMINI_API_KEY":
        return None, "API key not configured (placeholder in code)."
    try:
        response = model.generate_content([prompt])
        print("Full Gemini Response:")
        print(response)
        if response.candidates and len(response.candidates) > 0 and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                print(f"Checking Part:")
                print(part)
                if hasattr(part, "inline_data"):
                    print(f"Found inline_data:")
                    print(part.inline_data)
                    if hasattr(part.inline_data, "data") and hasattr(part.inline_data, "mime_type"):
                        base64_image = part.inline_data.data
                        mime_type = part.inline_data.mime_type
                        return {"mime_type": mime_type, "base64_data": base64_image}, None
                    else:
                        error_message = f"Could not find 'data' or 'mime_type' in inline_data. Data present: {hasattr(part.inline_data, 'data')}, Mime Type present: {hasattr(part.inline_data, 'mime_type')}"
                        print(error_message)
                        return None, error_message
                else:
                    print(f"Part does not have inline_data.")
            return None, "No image data found in the response parts with inline_data."
        else:
            return None, "No candidates or parts in the response."
    except Exception as e:
        return None, f"Error generating image: {e}"

def upload_image_to_gcs(image_data, mime_type):
    """Uploads base64 image data to Google Cloud Storage and returns the public URL."""
    if not GCS_PROJECT_ID or not GCS_BUCKET_NAME:
        print("Error: GCS_PROJECT_ID or GCS_BUCKET_NAME environment variables not set.")
        return None

    try:
        image_bytes = base64.b64decode(image_data)
        filename = f"generated_character_{int(time.time())}.{mime_type.split('/')[-1]}"
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"Error uploading to GCS: {e}")
        return None

# --- Flask Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.form['message']
    response_data = {"response": ""}

    if "generate an image of" in user_message.lower():
        description = user_message.lower().replace("generate an image of", "").strip()
        if description:
            image_info, error = generate_image_with_gemini(prompt)
            if image_info:
                image_url = upload_image_to_gcs(image_info['base64_data'], image_info['mime_type'])
                if image_url:
                    response_data["response"] = f"<img src='{image_url}' alt='Generated Character' style='max-width: 300px;'>"
                else:
                    response_data["response"] = "Error uploading image to cloud storage."
            else:
                response_data["response"] = f"Sorry, I couldn't generate the image. Error: {error}"
        else:
            response_data["response"] = "Please provide a description for the image you want to generate."
    else:
        response_data["response"] = "I can currently only generate images of game characters. Try saying 'generate an image of a tall, grey hair and have blue eyes character'."

    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True)