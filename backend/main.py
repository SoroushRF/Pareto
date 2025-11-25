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

def calculate_strategic_plan(data, target_grade):
    """
    Calculates the optimal strategy to achieve the target grade with minimum effort.
    """
    total_points = data.get('total_points', 100)
    assignments = data.get('assignments', [])
    
    # Calculate slack budget (points we can lose)
    # Assuming total_points is 100 for percentage based, or scaling accordingly
    # If total_points is not 100, we need to normalize or adjust target
    # For simplicity, assuming weights sum to 100 or total_points is the reference
    
    slack_budget = total_points * (1 - (target_grade / 100.0))
    current_slack_used = 0
    
    skipped_items = []
    must_do_items = []
    
    # Separate mandatory and optional
    mandatory = []
    optional = []
    
    for item in assignments:
        if item.get('mandatory', False):
            mandatory.append(item)
        else:
            optional.append(item)
            
    # Sort optional by weight (smallest first) to maximize number of skipped items
    # OR sort by weight (largest first) to maximize "effort" saved per item?
    # Usually "minimum effort" means skipping the biggest chunks of work possible?
    # But the prompt said "Sort non-mandatory items by weight (Smallest to Largest)" 
    # Wait, if I want to skip the MOST items, I skip small ones.
    # If I want to skip the MOST WORK (assuming weight ~ effort), I should skip large ones.
    # The user prompt said: "Sort non-mandatory items by weight (Smallest to Largest)."
    # Let's follow the user's instruction, although skipping small items first maximizes the COUNT of skipped items.
    
    optional.sort(key=lambda x: x['weight'])
    
    # "Spend" the slack budget
    for item in optional:
        weight = item['weight']
        if current_slack_used + weight <= slack_budget:
            current_slack_used += weight
            skipped_items.append({
                'name': item['name'],
                'reason': f"Weight {weight}% is within slack budget."
            })
        else:
            must_do_items.append({
                'name': item['name'],
                'reason': "Skipping this would drop grade below target."
            })
            
    # Add all mandatory to must_do
    for item in mandatory:
        must_do_items.append({
            'name': item['name'],
            'reason': "Mandatory assignment."
        })
        
    summary = f"You can skip {len(skipped_items)} assignments and still get {target_grade}%."
    
    return {
        "target_grade": target_grade,
        "slack_budget": round(slack_budget, 1),
        "must_do": must_do_items,
        "safe_to_skip": skipped_items,
        "summary": summary
    }

@app.get("/")
def read_root():
    return {"status": "Pareto Backend Online"}

@app.post("/analyze")
async def analyze_syllabus(file: UploadFile = File(...), target_grade: int = Form(80)):
    temp_filename = f"temp_{file.filename}"
    try:
        # Save the file temporarily
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Upload to Gemini
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        print(f"Uploading {temp_filename} to Gemini...")
        uploaded_file = genai.upload_file(temp_filename)
        
        # System prompt - Pure Extraction
        prompt = """Analyze this syllabus. Extract the grading schema. Return ONLY valid JSON.
   Structure:
   {
     'total_points': number (if not stated, assume 100),
     'assignments': [
       {'name': string, 'weight': number, 'mandatory': boolean}
     ],
     'policies': [
       {'rule': string, 'type': 'drop_lowest' OR 'penalty' OR 'other'}
     ]
   }"""

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
        
        # Calculate Strategy Deterministically
        strategy = calculate_strategic_plan(data, target_grade)
        data['strategy'] = strategy
        
        return data

    except Exception as e:
        # Cleanup if error occurs
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return {"error": str(e)}
