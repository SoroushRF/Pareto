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
    Calculates strategy based on the 3-State Logic (Mandatory, Transferable, Optional).
    """
    total_points = data.get('total_points', 100)
    assignments = data.get('assignments', [])
    
    # 1. Calculate Slack Budget (Points we can afford to burn)
    slack_budget = total_points * (1 - (target_grade / 100.0))
    current_slack_used = 0
    
    skipped_items = []
    must_do_items = []
    
    # 2. Filter lists based on the new 'category' field
    strictly_mandatory = [a for a in assignments if a.get('category') == 'strictly_mandatory']
    transferable = [a for a in assignments if a.get('category') == 'transferable']
    optional = [a for a in assignments if a.get('category') == 'optional']
    
    # 3. Sort optional by weight (smallest first)
    # We burn small items first to clear the board.
    optional.sort(key=lambda x: x['weight'])
    
    # 4. Phase 1: Skip "Optional" items (These consume the Slack Budget)
    for item in optional:
        weight = item['weight']
        if current_slack_used + weight <= slack_budget:
            current_slack_used += weight
            item['status'] = 'Skipped (Lost Points)'
            item['message'] = f"Skipping costs {weight}%, but you're still safe."
            skipped_items.append(item)
        else:
            item['status'] = 'Must Do'
            item['message'] = "Skipping this would drop you below target."
            must_do_items.append(item)

    # 5. Phase 2: Handle "Transferable" items
    # These DON'T use the budget, but they are high risk.
    for item in transferable:
        weight = item['weight']
        logic = item.get('transfer_logic', 'Weight transfers to another item.')
        
        # Heuristic: If it's huge (>25%), don't recommend skipping it via transfer (too risky).
        if weight < 25:
             item['status'] = 'Skipped (Transferred)'
             item['message'] = f"Strategy: {logic}. Prepare to grind later."
             skipped_items.append(item)
        else:
             item['status'] = 'Must Do (High Risk)'
             item['message'] = f"Too risky to rely on transfer: {logic}"
             must_do_items.append(item)

    # 6. Phase 3: Mandatory
    for item in strictly_mandatory:
        item['status'] = 'Critical'
        item['message'] = f"Syllabus Policy: {item.get('evidence', 'Must Submit')}"
        must_do_items.append(item)

    summary = f"You can skip {len(skipped_items)} assignments. {round(current_slack_used, 1)}% points burned."
    
    return {
        "target_grade": target_grade,
        "slack_budget": round(slack_budget, 1),
        "slack_used": round(current_slack_used, 1),
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
        prompt = """
You are a ruthless academic strategist. Your goal is to identify the MINIMUM path to passing. 
Analyze this syllabus PDF. Classify every single assignment.

Return ONLY valid JSON.

JSON STRUCTURE:
{
  "assignments": [
    {
      "name": string,
      "weight": number,
      "category": "strictly_mandatory" OR "transferable" OR "optional",
      "transfer_logic": string (e.g., "Weight moves to Final Exam" or null),
      "evidence": string (Direct quote proving the status)
    }
  ]
}

CRITICAL DEFINITIONS:
1. "strictly_mandatory": ASSIGN THIS ONLY IF THE SYLLABUS EXPLICITLY STATES FAILURE CONSEQUENCES. 
   - Examples: "Failure to attend lab results in F", "Must pass final to pass course".
   - Do NOT mark an assignment as mandatory just because it is worth a lot of points. 
   - Do NOT mark it mandatory just because the professor says "attendance is important". 
   - If I can get a 0% on it and NOT automatically fail the COURSE, it is NOT strictly_mandatory.

2. "transferable": Assignments where the weight shifts if missed.
   - Examples: "If midterm is missed, Final counts for 100%", "Best 5 out of 6 quizzes".

3. "optional": EVERYTHING ELSE. 
   - If I skip it, I get a 0. That is the only consequence.
   - Most Homework, Quizzes, and even Midterms (if no transfer rule exists) are Optional.
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
        
        # Calculate Strategy Deterministically
        strategy = calculate_strategic_plan(data, target_grade)
        data['strategy'] = strategy
        
        return data

    except Exception as e:
        # Cleanup if error occurs
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return {"error": str(e)}
