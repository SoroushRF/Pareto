import os
import shutil
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

genai.configure(api_key=api_key)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def organize_syllabus_data(data):
    """
    Cleans and organizes the extracted syllabus data.
    """
    total_points = data.get('total_points', 100)
    assignments = data.get('assignments', [])
    policies = data.get('policies', [])
    
    # Sort assignments by weight (descending)
    assignments.sort(key=lambda x: x.get('weight', 0), reverse=True)

    return {
        "total_points": total_points,
        "assignments": assignments, 
        "policies": policies
    }

@app.get("/")
def read_root():
    return {"status": "Pareto Backend Online"}

@app.post("/analyze")
async def analyze_syllabus(file: UploadFile = File(...)):
    temp_filename = f"temp_{file.filename}"
    try:
        # Save the file temporarily
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Upload to Gemini
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        print(f"Uploading {temp_filename} to Gemini...")
        uploaded_file = genai.upload_file(temp_filename)
        
        # System prompt - Pure Extraction
        prompt = """
            You are an expert academic strategist. Analyze the syllabus to determine the grading mechanism for every assessment.

            Return ONLY valid JSON.

            ### INSTRUCTIONS
            1. Analyze the text to find all assessments.
            2. Look for "Drop Rules" (e.g., "lowest 2 dropped") -> These are 'internal_drop'.
            3. Look for "Transfer Rules" (e.g., "missed midterm weight goes to final") -> These are 'external_transfer'.
            4. Look for "Strict Failures" (e.g., "must pass final to pass course") -> These are 'strictly_mandatory'.
            5. EVERYTHING ELSE is 'standard_graded' (meaning if you skip it, you lose the points, but don't auto-fail).
            6. Extract general "Policies" regarding late penalties, passing thresholds, or special conditions.

            ### ONE-SHOT LEARNING EXAMPLE (FOLLOW THIS PATTERN EXACTLY)

            Input Text excerpt:
            "Labs are worth 15%. The best 9 of 11 labs will be counted. 
            Participation is 10%, consisting of 3 lab check-ins (3%) and 10 of 14 lecture activities (7%).
            Midterms are 20%. If you miss the first midterm, its weight transfers to the second.
            The Final Exam is 35%. 
            Late labs are penalized 10% per day. You must pass the safety quiz to pass the course."

            Correct JSON Output:
            {
            "total_points": 100,
            "assignments": [
                {
                "name": "Labs",
                "weight": 15,
                "type": "internal_drop", 
                "details": { "drop_count": 2, "total_items": 11 },
                "evidence": "best 9 of 11 labs will be counted"
                },
                {
                "name": "Lab Check-ins",
                "weight": 3,
                "type": "standard_graded",
                "details": {},
                "evidence": "3 lab check-ins (3%)"
                },
                {
                "name": "Lecture Activities",
                "weight": 7,
                "type": "internal_drop",
                "details": { "drop_count": 4, "total_items": 14 },
                "evidence": "10 of 14 lecture activities"
                },
                {
                "name": "Midterm 1",
                "weight": 20,
                "type": "external_transfer",
                "details": { "transfer_target": "Midterm 2" },
                "evidence": "weight transfers to the second"
                },
                {
                "name": "Final Exam",
                "weight": 35,
                "type": "standard_graded",
                "details": {},
                "evidence": "Final Exam is 35%"
                },
                {
                "name": "Safety Quiz",
                "weight": 0,
                "type": "strictly_mandatory",
                "details": {},
                "evidence": "Must pass the safety quiz to pass the course"
                }
            ],
            "policies": [
                "Late labs are penalized 10% per day.",
                "Must pass the safety quiz to pass the course.",
                "Best 9 of 11 labs counted."
            ]
            }

            ### END EXAMPLE

            Now, analyze the user's PDF and return ONLY valid JSON matching this structure.

"""
        print("Generating content...")
        response = model.generate_content([prompt, uploaded_file])
        
        # Cleanup temp file
        os.remove(temp_filename)
        
        # Extract JSON from response
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        data = json.loads(text)
        
        # Organize Data
        organized_data = organize_syllabus_data(data)
        
        return organized_data

    except Exception as e:
        # Cleanup if error occurs
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return {"error": str(e)}
