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
    Calculates strategy distinguishing between Internal Drops (Freebies) and External Transfers.
    """
    total_points = data.get('total_points', 100)
    assignments = data.get('assignments', [])
    
    # 1. Calculate Slack Budget
    slack_budget = total_points * (1 - (target_grade / 100.0))
    current_slack_used = 0
    
    skipped_items = []
    must_do_items = []
    
    # 2. Logic Loop
    for item in assignments:
        category = item.get('type', 'optional') # strictly_mandatory, external_transfer, internal_drop, optional
        weight = item.get('weight', 0)
        name = item.get('name', 'Unknown')
        evidence = item.get('evidence', '')
        details = item.get('details', {})

        # CASE A: Internal Drop (The "Best X of Y" Scenario) - e.g., Labs
        # These are "Free Skips" that DO NOT consume your grade slack.
        if category == 'internal_drop':
            drop_count = details.get('drop_count', 0)
            total_items = details.get('total_sub_items', 0)
            
            if drop_count > 0:
                # Generate "Virtual" Skippable items for the free drops
                for i in range(int(drop_count)):
                    skipped_items.append({
                        'name': f"{name} - Skip #{i+1}",
                        'status': 'Free Skip',
                        'message': f"Allowed by policy: {evidence}",
                        'weight': 0 # Doesn't cost points
                    })
                
                # The REST of this component is effectively Mandatory (or Optional)
                # For safety, we list the "Core" component as Must Do, since you can't skip ALL of them.
                must_do_items.append({
                    'name': f"{name} (Core Required)",
                    'status': 'Must Do',
                    'message': f"You can skip {drop_count}, but must do the rest.",
                    'weight': weight
                })
            continue

        # CASE B: External Transfer (e.g., Midterm -> Final)
        # This shifts risk, doesn't burn slack.
        if category == 'external_transfer':
            target = details.get('transfer_target', 'Final Exam')
            # Heuristic: Only recommend transfer if the component is < 25%
            if weight < 25:
                skipped_items.append({
                    'name': name,
                    'status': 'Transferable',
                    'message': f"Weight moves to {target}. ({evidence})",
                    'weight': 0 # Points preserved, just moved
                })
            else:
                must_do_items.append({
                    'name': name,
                    'status': 'High Risk Transfer',
                    'message': f"Technically transferable to {target}, but risky ({weight}%).",
                    'weight': weight
                })
            continue

        # CASE C: Strictly Mandatory (Safety Labs, Etc)
        if category == 'strictly_mandatory':
            must_do_items.append({
                'name': name,
                'status': 'Critical',
                'message': "Explicit failure condition in syllabus.",
                'weight': weight
            })
            continue

        # CASE D: Optional (Standard Stuff) - This uses the Slack Budget
        # We process these in a second pass after identifying them, 
        # but for simplicity in this loop structure, let's bucket them now 
        # and sort/decide later.
        # We'll use a temp list for standard optional items.
        pass

    # 3. Process "Optional" items (The Knapsack Problem)
    # We filter the original list again just for 'optional' types to sort them properly
    optional_candidates = [a for a in assignments if a.get('type') == 'optional']
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
                'message': "Not enough slack budget left.",
                'weight': weight
            })

    summary = f"Strategy generated. Used {round(current_slack_used, 1)}% of your {round(slack_budget, 1)}% loss budget."

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
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        print(f"Uploading {temp_filename} to Gemini...")
        uploaded_file = genai.upload_file(temp_filename)
        
        # System prompt - Pure Extraction
        prompt = """
            You are an expert academic advisor helping a student optimize their semester strategy.
            Your goal is to read the syllabus and find every "loophole", "drop rule", or "weight transfer" policy.

            Analyze the grading scheme naturally. Don't just look for keywords; understand the MECHANISM of how grades are calculated.

            Return ONLY valid JSON.

            JSON STRUCTURE:
            {
            "total_points": number (usually 100),
            "assignments": [
                {
                "name": string,
                "weight": number,
                "type": "string", // ENUM: see definitions below
                "details": {
                    "drop_count": number (e.g., 2, if "lowest 2 dropped"),
                    "total_sub_items": number (e.g., 11, if "11 labs total"),
                    "transfer_target": string (e.g., "Final Exam", only for external transfers)
                },
                "evidence": string (Quote the text that explains this rule)
                }
            ],
            "policies": [ string ]
            }

            DEFINITIONS FOR "TYPE":

            1. "internal_drop": (The "Best X of Y" Rule)
            - Use this when a component is made of multiple small parts, and the lowest N are dropped.
            - Example: "Best 9 of 11 labs count", "Lowest quiz dropped".
            - This is NOT a transfer to the Final. It is an internal forgiveness policy.

            2. "external_transfer": (The "Shift" Rule)
            - Use this when missing an assignment moves its weight to a DIFFERENT assignment.
            - Example: "If Midterm is missed, weight is added to Final Exam".

            3. "strictly_mandatory": (The "Fail" Rule)
            - Use this ONLY if the syllabus explicitly says failure to complete results in failing the course.
            - "Attendance required" usually just means lost points (optional), NOT mandatory failure, unless explicitly stated "Automatic F".

            4. "optional": (The "Zero" Rule)
            - Standard assignments. If missed, you get a 0. No other magic happens.
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
