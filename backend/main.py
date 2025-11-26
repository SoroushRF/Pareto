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
    V4 Logic: Handles Internal Drops, External Transfers, and Standard Options.
    """
    total_points = data.get('total_points', 100)
    assignments = data.get('assignments', [])
    
    slack_budget = total_points * (1 - (target_grade / 100.0))
    current_slack_used = 0
    
    skipped_items = []
    must_do_items = []
    
    # --- PHASE 1: PROCESS SPECIAL TYPES ---
    for item in assignments:
        category = item.get('type', 'optional')
        weight = item.get('weight', 0)
        name = item.get('name', 'Assignment')
        details = item.get('details', {})

        # 1. INTERNAL DROPS (The "Freebies")
        if category == 'internal_drop':
            drop_count = details.get('drop_count', 0)
            if drop_count > 0:
                # Add the Free Skips
                for i in range(int(drop_count)):
                    skipped_items.append({
                        'name': f"{name} - Free Skip #{i+1}",
                        'status': 'Free Skip',
                        'message': f"Lowest grade dropped. (Weight: 0%)",
                        'weight': 0
                    })
                # The rest is technically Must Do (or Optional), 
                # but to simplify the UI, we mark the 'Core' as Must Do
                must_do_items.append({
                    'name': f"{name} (Remainder)",
                    'status': 'Must Do',
                    'message': f"You used your {drop_count} drops. The rest count.",
                    'weight': weight
                })
            continue

        # 2. EXTERNAL TRANSFERS (Risk Shifting)
        if category == 'external_transfer':
            target = details.get('transfer_target', 'Final Exam')
            if weight < 25:
                skipped_items.append({
                    'name': name,
                    'status': 'Transferable',
                    'message': f"Weight moves to {target}. No points lost.",
                    'weight': 0
                })
            else:
                must_do_items.append({
                    'name': name,
                    'status': 'High Risk Transfer',
                    'message': f"Too heavy ({weight}%) to transfer to {target}.",
                    'weight': weight
                })
            continue

        # 3. STRICTLY MANDATORY
        if category == 'strictly_mandatory':
            must_do_items.append({
                'name': name,
                'status': 'Critical',
                'message': "Explicit Failure Condition.",
                'weight': weight
            })
            continue

        # 4. OPTIONAL (Will process in Phase 2)
        item['_is_standard_optional'] = True

    # --- PHASE 2: THE KNAPSACK (Standard Optional Items) ---
    optional_candidates = [a for a in assignments if a.get('_is_standard_optional')]
    optional_candidates.sort(key=lambda x: x['weight'])

    for item in optional_candidates:
        weight = item['weight']
        if current_slack_used + weight <= slack_budget:
            current_slack_used += weight
            skipped_items.append({
                'name': item['name'],
                'status': 'Skipped',
                'message': f"Burned {weight}% of slack budget.",
                'weight': weight
            })
        else:
            must_do_items.append({
                'name': item['name'],
                'status': 'Must Do',
                'message': "Not enough slack budget.",
                'weight': weight
            })

    summary = f"Strategy: {len(skipped_items)} items skipped. {round(current_slack_used, 1)}% budget used."

    return {
        "total_points": total_points,
        "assignments": assignments, 
        "policies": data.get('policies', []),
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
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        print(f"Uploading {temp_filename} to Gemini...")
        uploaded_file = genai.upload_file(temp_filename)
        
        # System prompt - Pure Extraction
        prompt = """
            You are an expert academic strategist. Your goal is to extract the grading scheme from a syllabus.
            You must distinguish between "Mandatory" work, "Optional" work (lost points), and "Transferable" work (risk shifting).

            ### INSTRUCTIONS
            1. Analyze the text to find all assessments.
            2. Look for "Drop Rules" (e.g., "lowest 2 dropped") -> These are 'internal_drop'.
            3. Look for "Transfer Rules" (e.g., "missed midterm weight goes to final") -> These are 'external_transfer'.
            4. Look for "Strict Failures" (e.g., "must pass final to pass course") -> These are 'strictly_mandatory'.
            5. EVERYTHING ELSE is 'optional' (meaning if you skip it, you get a 0, but don't auto-fail).

            ### ONE-SHOT LEARNING EXAMPLE (FOLLOW THIS PATTERN EXACTLY)

            Input Text excerpt:
            "Labs are worth 15%. The best 9 of 11 labs will be counted. 
            Participation is 10%, consisting of 3 lab check-ins (3%) and 10 of 14 lecture activities (7%).
            Midterms are 20%. If you miss the first midterm, its weight transfers to the second."

            Correct JSON Output:
            {
            "total_points": 100,
            "assignments": [
                {
                "name": "Labs",
                "weight": 15,
                "type": "internal_drop", 
                "details": { "drop_count": 2, "total_sub_items": 11 },
                "evidence": "best 9 of 11 labs will be counted"
                },
                {
                "name": "Lab Check-ins",
                "weight": 3,
                "type": "optional",
                "evidence": "3 lab check-ins (3%)"
                },
                {
                "name": "Lecture Activities",
                "weight": 7,
                "type": "internal_drop",
                "details": { "drop_count": 4, "total_sub_items": 14 },
                "evidence": "10 of 14 lecture activities"
                },
                {
                "name": "Midterm 1",
                "weight": 20,
                "type": "external_transfer",
                "details": { "transfer_target": "Midterm 2" },
                "evidence": "weight transfers to the second"
                }
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
        
        # Calculate Strategy Deterministically
        strategy = calculate_strategic_plan(data, target_grade)
        data['strategy'] = strategy
        
        return data

    except Exception as e:
        # Cleanup if error occurs
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return {"error": str(e)}
