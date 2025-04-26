# app.py
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from deep_translator import GoogleTranslator
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure the Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY', ""))
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    safety_settings={
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
)

# Supported Indian languages with their codes
INDIAN_LANGUAGES = {
    'hi': 'Hindi',
    'bn': 'Bengali',
    'te': 'Telugu',
    'ta': 'Tamil',
    'mr': 'Marathi',
    'gu': 'Gujarati',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'pa': 'Punjabi',
    'or': 'Odia',
    'as': 'Assamese',
    'en': 'English'  # Default
}

@app.route('/')
def index():
    return render_template('index.html', languages=INDIAN_LANGUAGES)

@app.route('/check_symptoms', methods=['POST'])
def check_symptoms():
    data = request.get_json()
    symptoms = data.get('symptoms', '')
    age = data.get('age', '')
    gender = data.get('gender', '')
    language = data.get('language', 'en')
    
    # If language is not English, translate symptoms to English
    original_symptoms = symptoms
    if language != 'en':
        try:
            # Using deep_translator's GoogleTranslator
            translator = GoogleTranslator(source=language, target='en')
            symptoms = translator.translate(symptoms)
        except Exception as e:
            return jsonify({'error': f'Translation error: {str(e)}'})
    
    # Format the prompt with all available information
    prompt = f"""
    Act as a medical assistant providing initial assessment. This is NOT a substitute for professional medical advice.
    
    Patient details:
    - Age: {age}
    - Gender: {gender}
    - Symptoms: {symptoms}
    
    Please provide:
    1. A brief assessment of possible conditions
    2. Severity level (Low, Medium, High)
    3. Recommended next steps (home care, consult doctor, emergency)
    4. General care suggestions
    
    Format the response as JSON with keys: "possible_conditions", "severity", "next_steps", "care_suggestions", and "disclaimer".
    """
    
    try:
        # Generate response from Gemini
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Extract JSON from the response
        # Try to find JSON in the response which might be surrounded by markdown code blocks
        if "```json" in response_text:
            json_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_text = response_text.split("```")[1].strip()
        else:
            json_text = response_text.strip()
        
        try:
            result = json.loads(json_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, create a structured response manually
            result = {
                "possible_conditions": ["Unable to parse AI response properly"],
                "severity": "Unknown",
                "next_steps": "Please consult a healthcare professional for proper assessment.",
                "care_suggestions": ["Seek professional medical advice"],
                "disclaimer": "This is not medical advice. Please consult a healthcare professional for proper diagnosis."
            }
        
        # Add standard disclaimer if not present
        if "disclaimer" not in result:
            result["disclaimer"] = "This is not medical advice. Please consult a healthcare professional for proper diagnosis."
            
        # If language is not English, translate the result back
        if language != 'en':
            try:
                # Create translator for reverse translation
                translator = GoogleTranslator(source='en', target=language)
                
                for key in result:
                    if isinstance(result[key], str):
                        result[key] = translator.translate(result[key])
                    elif isinstance(result[key], list):
                        translated_list = []
                        for item in result[key]:
                            if isinstance(item, str):
                                translated_list.append(translator.translate(item))
                            else:
                                translated_list.append(item)
                        result[key] = translated_list
            except Exception as e:
                return jsonify({'error': f'Translation error: {str(e)}'})
        
        # Add original and translated symptoms for reference
        result["original_input"] = original_symptoms
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'Error processing request: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)