import os
import shutil
import json
import time
from typing import List, Optional, Any, Dict, Union
from fastapi import Request
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import google.generativeai as genai
from pydantic import BaseModel, Field

# 1. SETUP
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key: print("Warning: GEMINI_API_KEY not found.")
genai.configure(api_key=api_key)

# PRESERVING YOUR CHOICE: Gemini 2.5 Flash
model = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. PYDANTIC MODELS (Strict Validation for Critical Data)
# ==========================================

class GradingMechanic(BaseModel):
    # FIX: Changed 'bool' to 'Optional[bool]' to handle nulls
    is_mandatory_submission: Optional[bool] = False
    drop_lowest_n: Optional[int] = 0
    grading_method: Optional[str] = None

class WeightTransfer(BaseModel):
    trigger: Optional[str] = None
    condition: Optional[str] = None
    target_assessment_id: Optional[str] = None

# --- PASTE THIS BLOCK TO FIX THE ATTRIBUTE ERROR ---

class DateInfo(BaseModel):
    due_date: Optional[str] = None
    # FIX: Changed 'bool' to 'Optional[bool]' to handle nulls safely
    is_scheduled_event: Optional[bool] = False
    location_override: Optional[str] = None

class AssessmentComponent(BaseModel):
    id: Optional[str] = None
    name: str = "Unknown Assignment"
    category: Optional[str] = None
    
    # FIX 1: Allow Strings (e.g., "Variable") instead of crashing
    weight_percentage: Optional[Union[float, str]] = 0.0
    
    # FIX 2: Allow Strings (e.g., "See eClass") 
    quantity: Optional[Union[int, str]] = 1
    
    # FIX 3: Explicitly allow None for dates
    dates: Optional[DateInfo] = Field(default_factory=DateInfo)
    
    grading_mechanics: GradingMechanic = Field(default_factory=GradingMechanic)
    weight_transfer_logic: List[WeightTransfer] = []
    evidence: Optional[str] = None

class AssessmentStructure(BaseModel):
    components: List[AssessmentComponent] = []

class GlobalPolicies(BaseModel):
    lateness_policy: Optional[Dict[str, Any]] = None
    missed_work_policy: Optional[Dict[str, Any]] = None
    academic_integrity: Optional[Dict[str, Any]] = None

class OmniscientSyllabus(BaseModel):
    """
    Validates the critical 'Pareto' data.
    ALLOWS extra fields (the 80% junk) to pass through without crashing.
    """
    assessment_structure: AssessmentStructure = Field(default_factory=AssessmentStructure)
    global_policies: GlobalPolicies = Field(default_factory=GlobalPolicies)
    
    # CRITICAL: This allows 'materials_and_costs', 'logistics', etc. to pass through safely.
    model_config = {"extra": "allow"}

# ==========================================
# 3. THE OMNISCIENT SYSTEM PROMPT (Verbatim 5.1 Template)
# ==========================================

system_prompt = """
{
You are an expert Academic Auditor and Logic Engine. Your goal is NOT just to "read" the syllabus, but to **deconstruct** it into a rigid, deterministic database.

### 🛑 PRIME DIRECTIVE: THE "REALITY CHECK"
You must filter out "Noise" vs. "Gradeable Work".
1.  **If it doesn't have a Weight (%) or Point Value, it DOES NOT EXIST.**
    * Ignore "Learning Outcomes" (CLOs), "Weekly Topics", or "Suggested Readings" unless they are explicitly graded.
    * Ignore "Class Activities" if they are vague participation requirements without a specific percentage attached.
2.  **If it looks like a header, ignore it.**
    * Example: If the text says "Assessments: 1. Midterm 2. Final", do NOT create an item called "Assessments". Create items for "Midterm" and "Final".

### ⚡ CRITICAL LOGIC: SPLITTING GROUPED ITEMS (THE "ATOMIC" RULE)
Syllabi often group items like "Midterms (2) ... 20%".
You must **SPLIT** these into individual atomic entries in the `components` list.
* **WRONG:** `{ "name": "Midterms", "quantity": 2, "weight": 20 }`
* **RIGHT:**
    * Item 1: `{ "name": "Midterm 1", "weight": 10, "quantity": 1 }`
    * Item 2: `{ "name": "Midterm 2", "weight": 10, "quantity": 1 }`

**WHY?** Because transfer logic relies on distinct events. "Midterm 1 transfers to Midterm 2" is impossible if they are one entry.
* *Exception:* If they are truly identical small items (e.g., "Weekly Quizzes (10)"), you may group them as `{ "name": "Weekly Quizzes", "quantity": 10 }` ONLY IF no specific dates or distinct transfer rules apply to specific ones.

### 🔍 EVIDENCE CONSTRAINT (NO WALLS OF TEXT)
Your `evidence` field is for **Verification**, not summarization.
* **Strict Limit:** Maximum 1-2 sentences.
* **Content:** Quote the **exact specific line** that defines the weight, drop rule, or transfer policy.
* **Do Not:** Copy entire paragraphs about academic integrity into the assignment evidence.

### 📝 FIELD-SPECIFIC RULES
1.  **Dates:** Convert ALL dates to strict `YYYY-MM-DD` format. If the year is missing, infer `2025` (or current academic year). If a date is a range (e.g., "Week of Oct 2"), use the Monday of that week.
2.  **Mandatory Status (`grading_mechanics`):**
    * `is_mandatory_submission`: **TRUE** ONLY if the syllabus explicitly says "Failure to submit results in F" or "Must pass this component to pass course".
    * **FALSE** for everything else (even if it's worth 50%). A zero is not a failure of the *course*, it's just a zero.
3.  **Transfer Logic:**
    * If text says "Higher mark counts", this is a Transfer Rule.
    * If text says "Missed test weight moves to final", this is a Transfer Rule.
4.  **Booleans:** Never return null for boolean fields (like `is_mandatory` or `is_scheduled_event`). Use `false` as the default if the syllabus doesn't explicitly say "True/Yes".

### 📄 THE OUTPUT TEMPLATE
You must output valid JSON that strictly adheres to this schema. Do not add keys. Do not remove keys. Fill every field. If data is missing, use `null`.

  "_template_version": "5.1 - The 'Omniscient' Final Standard (Corrected)",
  "_description": "The ultimate syllabus analysis structure. Handles every conceivable grading logic, accreditation detail, logistical nuance, and event scheduling requirement found in Engineering/University courses.",
  
  "syllabus_metadata": {
    "source_file_name": "String (e.g., 'syllabus.pdf')",
    "last_updated_date": "String (Date found in document)",
    "academic_year": "String (e.g., '2025-2026')",
    "parsing_notes": "String (Any AI observations about the file quality or missing pages)"
  },

  "course_identity": {
    "code": "String (e.g., 'SC/PHYS 1800')",
    "title": "String (e.g., 'Engineering Mechanics')",
    "department": "String (e.g., 'EECS', 'Physics')",
    "faculty": "String (e.g., 'Lassonde School of Engineering')",
    "term": "String (e.g., 'Fall 2025')",
    "credits": "Number (e.g., 3.0 or 4.0)",
    "section_info": [
        {
            "section_code": "String (e.g., 'Section Z')",
            "delivery_mode": "String (e.g., 'In-Person', 'Blended', 'Remote', 'HyFlex')",
            "meeting_link": "String (Zoom/Teams link if provided)"
        }
    ],
    "prerequisites": ["String (List of course codes)"],
    "corequisites": ["String (List of course codes)"],
    "exclusions": ["String (List of courses that cannot be taken for credit if this is taken)"]
  },

  "accreditation_and_attributes": {
    "_comment": "Crucial for Engineering students tracking CEAB requirements and Competency-Based Grading.",
    "ceab_units": {
      "math": "Number (Percentage or Unit Count)",
      "natural_science": "Number",
      "engineering_science": "Number",
      "engineering_design": "Number",
      "complementary_studies": "Number"
    },
    "graduate_attributes": [
      {
        "attribute_code": "String (e.g., 'KB.1', '3.1', 'CLO 1')",
        "description": "String (e.g., 'Knowledge Base', 'Investigation', 'Ethics')",
        "assessment_link": "String (IDs of the assignments that measure this attribute, e.g., 'assignment_1, final_exam')"
      }
    ]
  },

  "learning_outcomes": [
    {
      "id": "String (e.g., 'CLO-1')",
      "description": "String (e.g., 'Analyze circuits using Ohm's Law')",
      "level": "String (e.g., 'Introductory', 'Intermediate', 'Advanced')"
    }
  ],

  "staff_and_support": [
    {
      "role": "String (e.g., 'Instructor', 'Lab Coordinator', 'TA', 'Technician', 'Peer Mentor')",
      "name": "String",
      "email": "String",
      "office_location": "String",
      "office_hours": ["String (e.g., 'Wed 3:00-4:30 PM')"],
      "communication_policy": "String (e.g., 'Must use subject line [EECS1011]', 'Use eClass chat only', 'No emails')",
      "responsibilities": "String (e.g., 'Contact for lab hardware issues only', 'Grading inquiries')"
    }
  ],

  "logistics_and_schedule": {
    "lecture_times": [
        {
            "section": "String",
            "time": "String (e.g., 'Mon/Wed 2:30 PM')",
            "location": "String (e.g., 'LAS A')"
        }
    ],
    "tutorial_times": ["String"],
    "lab_times": ["String (e.g., 'Weekly, check individual schedule')"],
    "exam_period_window": "String (e.g., 'Dec 4 - Dec 19')"
  },

  "materials_and_costs": [
    {
      "category": "String (e.g., 'Textbook', 'Hardware', 'Software', 'PPE', 'Subscription')",
      "name": "String (e.g., 'Arduino Starter Kit', 'Safety Glasses', 'iClicker App')",
      "cost_estimate": "String (e.g., '$89.95 + HST')",
      "is_mandatory": "Boolean",
      "purchase_info": "String (e.g., 'Bookstore only', 'Download link', 'Class Key: 1234')",
      "borrowing_info": "String (e.g., 'Student government exchange available', 'Library loan')",
      "technical_requirements": "String (e.g., 'Personal laptop required', 'Windows/Mac only', 'Webcam required')"
    }
  ],

  "safety_and_requirements": {
    "_comment": "Specific to labs, workshops, and experiential events.",
    "mandatory_training": ["String (e.g., 'WHMIS Level 1', 'Machine Shop Safety')"],
    "ppe_requirements": ["String (e.g., 'Closed-toe shoes', 'Lab Coat', 'Safety Goggles')"],
    "conduct_rules": "String (e.g., 'No food or drink in the lab', 'Netiquette applies')"
  },

  "grading_scheme": {
    "grading_scale_type": "String (e.g., 'Percentage', 'Letter Grade', 'Pass/Fail', 'Competency-Based')",
    "letter_grade_map": [
        {
            "grade": "String (e.g., 'A+')",
            "percent_range": "String (e.g., '90-100')",
            "gpa_value": "Number (e.g., 9.0)"
        }
    ],
    "curve_policy": "String (e.g., 'Grades may be adjusted to conform to Faculty distribution profiles', 'Second Chance Exam')"
  },

  "assessment_structure": {
    "_comment": "The core analysis block. 'pass_requirement' means you fail the course if you fail this component.",
    "components": [
      {
        "id": "String (Unique ID, e.g., 'midterm_1', 'unhack_event')",
        "name": "String (Display name, e.g., 'Midterm Exam 1', 'UNHack')",
        "evidence": "String (CRITICAL: QUOTE THE TEXT PROVING THE RULES HERE FIRST)",
        "category": "String (e.g., 'Exams', 'Labs', 'Participation', 'Project', 'Experiential Learning')",
        "weight_percentage": "Number (0-100, or 'Variable' if optimization logic exists)",
        "quantity": "Number (How many items in this group, e.g., 1 or 11)",
        
        "dates": {
            "due_date": "String (The official deadline, e.g., 'Oct 31 at 11:59 PM')",
            "recommended_completion_date": "String (For soft deadlines, e.g., 'Sept 19')",
            "hard_deadline": "String (If different from due date, e.g., '5 days late cutoff')",
            "grace_period": "String (e.g., '15 minutes buffer')",
            
            "is_scheduled_event": "Boolean (TRUE if this is a Hackathon, Exam, or Lab session you must ATTEND. FALSE if it is just a file upload.)",
            "event_duration": "String (e.g., '3 hours', '3 days', '50 minutes')",
            "recurrence": "String (e.g., 'One-time', 'Weekly', 'Bi-weekly')",
            "location_override": "String (e.g., 'BEST Lab', 'Exam Centre' - if different from Lecture)"
        },

        "grading_mechanics": {
          "is_mandatory_submission": "Boolean (Must submit/attend to pass?)",
          "component_pass_threshold": "Number (e.g., 50.0 - Must earn >50% on this specific item to pass course, else F)",
          "drop_lowest_n": "Number (e.g., 2 - Drops the lowest 2 grades in this category)",
          "attempts_allowed": "String (e.g., 'Unlimited', 'Single Attempt', 'Resubmission if <70%')",
          "grading_method": "String (e.g., 'Best of N', 'Average', 'Most Recent', 'Rubric by CLO', 'All-or-Nothing')"
        },

        "weight_transfer_logic": [
          {
            "trigger": "String (e.g., 'Missed with Documentation', 'Missed without Documentation', 'Performance Optimization', 'Missed Submission')",
            "condition": "String (e.g., 'If Final Exam Score > Midterm Score', 'Automatic if missed', 'If not opened by deadline')",
            "target_assessment_id": "String (ID of the assessment that receives this weight, e.g., 'final_exam')",
            "percentage_transfer": "Number (Usually 100, meaning 100% of this weight moves. Or 20, etc.)"
          }
        ],

        "constraints_and_tools": {
            "format": "String (e.g., 'In-Person', 'Online WebWork', 'Take-Home', 'Hackathon')",
            "location_requirement": "String (e.g., 'Must be done in Lab LAS 2001', 'On Campus')",
            "proctoring": "String (e.g., 'None', 'ProctorTrack', 'In-Person Invigilator')",
            "collaboration_policy": "String (e.g., 'Individual', 'Pairs Allowed', 'Group of 4', 'Learning Pods')",
            "allowed_aids": ["String (e.g., 'Crib sheet 8.5x11', 'Non-programmable calculator', 'Open Book')"],
            "banned_aids": ["String (e.g., 'Smartwatches', 'GenAI tools', 'Chegg')"],
            "ai_policy": "String (e.g., 'Banned', 'Allowed with Citation', 'Encouraged', 'Transparency Required')"
        },

        "group_work_details": {
            "_comment": "Only applicable if collaboration_policy indicates group work.",
            "team_formation": "String (e.g., 'Self-selected', 'Instructor-assigned', 'Random', 'Pods')",
            "peer_evaluation": "String (e.g., 'Peer evaluation determines 20% of grade', 'None')"
        },

        "special_grading_logic": {
            "_comment": "For complex rules that don't fit standard fields.",
            "type": "String (e.g., 'Threshold', 'Substitution', 'Matrix')",
            "description": "String (e.g., 'Must pass 4/5 thresholds to get 5% grade', 'Assignment 6 counts for CLO 3 and CLO 5')"
        }
      }
    ]
  },

  "detailed_schedule": {
    "_comment": "Granular breakdown of what happens each week/lecture.",
    "modules": [
        {
            "week_number": "Number or String (e.g., 'Week 1')",
            "date_range": "String",
            "topic": "String",
            "readings": "String",
            "associated_deliverables": ["String (IDs of assignments due this week)"]
        }
    ]
  },

  "global_policies": {
    "lateness_policy": {
      "penalty_per_day": "String (e.g., '10% deduction', 'Zero credit')",
      "max_late_days": "Number (e.g., 5)",
      "hard_cutoff_trigger": "String (e.g., 'Submission > 7 days late receives 0', 'Day of Final Exam')",
      "weekend_inclusion": "Boolean (Do weekends count as late days?)",
      "exceptions": "String (e.g., 'One-time strict pass available', 'Lowest 2 dropped for any reason')"
    },
    
    "missed_work_policy": {
      "general_procedure": "String (e.g., 'Weight transfers to final. No makeups.')",
      "documentation_required": "Boolean (Is a doctor's note needed?)",
      "self_declaration_allowed": "Boolean (Can you just email to say you are sick?)",
      "limitations": "String (e.g., 'Max 1 self-declaration per term', 'Deferral request within 1 week')"
    },

    "academic_integrity": {
      "general_statement": "String",
      "ai_tools_rules": "String (Specific rules on ChatGPT/Copilot)",
      "code_reuse_rules": "String (e.g., 'Self-plagiarism forbidden', '0 marks for unoriginal code')",
      "sharing_rules": "String (e.g., 'Uploading to CourseHero/Chegg is a violation')"
    },

    "intellectual_property": {
        "lecture_recordings": "String (e.g., 'Instructor copyright, no distribution', 'Zoom notifies when recording')",
        "student_work": "String (e.g., 'Student retains copyright but grants license to University')"
    },

    "accessibility_and_accommodations": {
      "contact_point": "String (e.g., 'Student Accessibility Services')",
      "deadline_for_requests": "String (e.g., 'First 3 weeks of term', 'As early as possible')",
      "religious_observance_policy": "String"
    }
  },

  "calendar_events": [
    {
        "date": "String (ISO Date or Descriptive)",
        "event_type": "String (e.g., 'Exam', 'Holiday', 'Drop Deadline', 'Withdrawal Deadline', 'Mandatory Event')",
        "description": "String"
    }
  ]
}
"""

# ==========================================
# 4. LOGIC ADAPTER
# ==========================================

def organize_syllabus_data(raw_data: dict):
    print("DEBUG: Starting organize_syllabus_data...")
    
    # 1. Validation
    try:
        syllabus = OmniscientSyllabus(**raw_data)
        print("DEBUG: Pydantic Validation PASSED (Strict).")
    except Exception as e:
        print(f"DEBUG: Validation Warning (Soft Fail): {e}")
        syllabus = OmniscientSyllabus.construct(**raw_data)

    # 2. Map to Pareto UI
    pareto_assignments = []
    
    # Safety check for components
    components = []
    if hasattr(syllabus, 'assessment_structure') and syllabus.assessment_structure:
         components = syllabus.assessment_structure.components

    print(f"DEBUG: Processing {len(components)} components...")

    for comp in components:
        category_type = "standard_graded"
        details = {}
        
        # Logic: Drop Rules
        if comp.grading_mechanics.drop_lowest_n and comp.grading_mechanics.drop_lowest_n > 0:
            category_type = "internal_drop"
            details = {"drop_count": comp.grading_mechanics.drop_lowest_n, "total_items": comp.quantity}
        # Logic: Transfers
        elif len(comp.weight_transfer_logic) > 0:
            category_type = "external_transfer"
            details = {"transfer_target": comp.weight_transfer_logic[0].target_assessment_id}
        # Logic: Mandatory
        elif comp.grading_mechanics.is_mandatory_submission:
            category_type = "strictly_mandatory"
            
        # --- THIS IS THE MISSING BLOCK YOU NEED ---
        due_date = None
        # Check if the nested 'dates' object exists
        if comp.dates and comp.dates.due_date:
            due_date = comp.dates.due_date
        # -----------------------------------------

        pareto_assignments.append({
            "name": comp.name,
            "weight": comp.weight_percentage,
            "type": category_type,
            "details": details,
            "evidence": comp.evidence or "No evidence extracted",
            "due_date": due_date  # <--- This failed because the block above was missing
        })

    # Sort
    # Sort
    priority_map = {"strictly_mandatory": 3, "standard_graded": 2, "external_transfer": 1, "internal_drop": 0}
    
    # FIX: Helper function to safely extract a numeric weight for sorting
    def get_safe_weight(item):
        w = item.get('weight', 0)
        if isinstance(w, (int, float)):
            return w
        return 0  # If it's a string like "Variable", treat it as 0 for sorting

    pareto_assignments.sort(key=lambda x: (
        priority_map.get(x['type'], 0), 
        get_safe_weight(x)
    ), reverse=True)
    # Policies
    policies = []
    gp = syllabus.global_policies
    if gp.lateness_policy and isinstance(gp.lateness_policy, dict):
        policies.append(f"Late Policy: {gp.lateness_policy.get('penalty_per_day', 'See syllabus')}")
    if gp.missed_work_policy and isinstance(gp.missed_work_policy, dict):
        policies.append(f"Missed Work: {gp.missed_work_policy.get('general_procedure', 'See syllabus')}")

    print("DEBUG: Organization complete. Returning data.")
    return {
        "total_points": 100,
        "assignments": pareto_assignments,
        "policies": policies,
        "raw_omniscient_json": raw_data
    }
# ==========================================
# 5. API
# ==========================================

@app.get("/")
def read_root():
    return {"status": "Pareto Backend Online"}
# Ensure Request is imported: 
# from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request

@app.post("/analyze")
async def analyze_syllabus(request: Request, file: UploadFile = File(...)): # <--- ADDED request: Request
    print(f"\n--- NEW REQUEST: {file.filename} ---")
    start_time = time.time()
    temp_filename = f"temp_{file.filename}"
    
    try:
        # 1. Save File
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"DEBUG: File saved locally ({time.time() - start_time:.2f}s)")

        # Quick check before heavy upload
        if await request.is_disconnected():
            print("⚠️ Client disconnected before upload. Aborting.")
            os.remove(temp_filename)
            return

        print(f"DEBUG: Uploading {temp_filename} to Gemini...")
        uploaded_file = genai.upload_file(temp_filename)
        print(f"DEBUG: Upload complete ({time.time() - start_time:.2f}s). Starting Generation...")
        
        # 2. Generate with Streaming
        response_stream = await model.generate_content_async(
            [system_prompt, uploaded_file], 
            stream=True
        )
        
        # 3. Build Response Chunk by Chunk + MONITOR CONNECTION
        full_text = ""
        print(f"DEBUG: Streaming response...")
        
        async for chunk in response_stream:
            # --- THE FIX: PULSE CHECK ---
            # Every time Google sends a chunk, we check if the User is still connected.
            if await request.is_disconnected():
                print(f"🛑 OPERATION ABORTED: User disconnected at {time.time() - start_time:.2f}s")
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
                return # Hard Stop
            # ----------------------------

            if chunk.text:
                full_text += chunk.text
        
        print(f"DEBUG: Generation complete ({time.time() - start_time:.2f}s)")
        os.remove(temp_filename)
        
        # 4. Parse Response (Standard logic continues...)
        # Only runs if user stayed connected the whole time
        text = full_text
        print("DEBUG: Raw text received (First 100 chars):", text[:100])
        
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        print("DEBUG: JSON parsed successfully. Running Logic Adapter...")
        raw_data = json.loads(text)
        
        if "syllabus_metadata" not in raw_data:
            raw_data["syllabus_metadata"] = {}
            
        raw_data["syllabus_metadata"]["source_file_name"] = file.filename

        return organize_syllabus_data(raw_data)

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return {"error": str(e)}