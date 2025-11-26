import os
import shutil
import json
import time
from typing import List, Optional, Any, Dict
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
    is_scheduled_event: bool = False
    location_override: Optional[str] = None

class AssessmentComponent(BaseModel):
    id: Optional[str] = None
    name: str = "Unknown Assignment"
    weight_percentage: float = 0.0
    
    # FIX: Optional int handles nulls
    quantity: Optional[int] = 1
    
    # FIX: This is the missing field that caused your crash!
    dates: DateInfo = Field(default_factory=DateInfo)
    
    # FIX: GradingMechanic must be defined above this class
    grading_mechanics: GradingMechanic = Field(default_factory=GradingMechanic)
    weight_transfer_logic: List[WeightTransfer] = []
    
    # Evidence at the bottom is fine since we force Gemini to find it first in prompt
    evidence: Optional[str] = None
    
    # Allow extra fields just in case
    model_config = {"extra": "allow"}
    
    # FIX: Changed 'int' to 'Optional[int]' to handle nulls
    quantity: Optional[int] = 1
    
    # We will fix the Date issue in the next step, keep this commented or flat for now
    # to focus strictly on the crash you saw.
    due_date: Optional[str] = None 
    
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

    "intellectual_property": {
        "lecture_recordings": "String (e.g., 'Instructor copyright, no distribution', 'Zoom notifies when recording')",
        "student_work": "String (e.g., 'Student retains copyright but grants license to University')"
    },
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
    # 1. Validation (Soft)
    try:
        # Pydantic validates 'assessment_structure' and 'global_policies'
        # Ignores 'materials_and_costs', 'course_identity' etc. (but keeps them)
        syllabus = OmniscientSyllabus(**raw_data)
    except Exception as e:
        print(f"Validation Warning: {e}")
        syllabus = OmniscientSyllabus.construct(**raw_data)

    # 2. Map to Pareto UI
    pareto_assignments = []
    
    components = []
    if hasattr(syllabus, 'assessment_structure') and syllabus.assessment_structure:
         components = syllabus.assessment_structure.components

    for comp in components:
        category_type = "standard_graded"
        details = {}
        
        # Check Drop Rules
        if comp.grading_mechanics.drop_lowest_n and comp.grading_mechanics.drop_lowest_n > 0:
            category_type = "internal_drop"
            details = {"drop_count": comp.grading_mechanics.drop_lowest_n, "total_items": comp.quantity}
        # Check Transfer Rules
        elif len(comp.weight_transfer_logic) > 0:
            category_type = "external_transfer"
            details = {"transfer_target": comp.weight_transfer_logic[0].target_assessment_id}
        # Check Mandatory
        elif comp.grading_mechanics.is_mandatory_submission:
            category_type = "strictly_mandatory"
            
        # EXTRACT DATE FIX
        due_date = None
        if comp.dates and comp.dates.due_date:
            due_date = comp.dates.due_date

        pareto_assignments.append({
            "name": comp.name,
            "weight": comp.weight_percentage,
            "type": category_type,
            "details": details,
            "evidence": comp.evidence or "No evidence extracted",
            "due_date": due_date
        })

    # Sort
    priority_map = {"strictly_mandatory": 3, "standard_graded": 2, "external_transfer": 1, "internal_drop": 0}
    pareto_assignments.sort(key=lambda x: (priority_map.get(x['type'], 0), x['weight']), reverse=True)

    # Policies Extraction (Flattening the nested objects for UI)
    policies = []
    gp = syllabus.global_policies
    
    # Helper to safe-extract string summaries from dictionaries
    if gp.lateness_policy and isinstance(gp.lateness_policy, dict):
        policies.append(f"Late Policy: {gp.lateness_policy.get('penalty_per_day', 'See syllabus')}")
    if gp.missed_work_policy and isinstance(gp.missed_work_policy, dict):
        policies.append(f"Missed Work: {gp.missed_work_policy.get('general_procedure', 'See syllabus')}")
    if gp.academic_integrity and isinstance(gp.academic_integrity, dict):
        policies.append("Academic Integrity: Strict rules apply (see raw data).")

    return {
        "total_points": 100,
        "assignments": pareto_assignments,
        "policies": policies,
        "raw_omniscient_json": raw_data # The Full Payload for Download
    }

# ==========================================
# 5. API
# ==========================================

@app.get("/")
def read_root():
    return {"status": "Pareto Backend Online"}

@app.post("/analyze")
async def analyze_syllabus(file: UploadFile = File(...)):
    print(f"\n--- NEW REQUEST: {file.filename} ---")
    start_time = time.time()
    temp_filename = f"temp_{file.filename}"
    try:
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            print(f"DEBUG: File saved locally ({time.time() - start_time:.2f}s)")
            print(f"DEBUG: Uploading {temp_filename} to Gemini...")

        print(f"Uploading {temp_filename} to Gemini...")
        uploaded_file = genai.upload_file(temp_filename)
        print(f"DEBUG: Upload complete ({time.time() - start_time:.2f}s). Starting Generation...")
        
        # Generate with the Full 5.1 Prompt
        response = model.generate_content([system_prompt, uploaded_file])
        print(f"DEBUG: Generation complete ({time.time() - start_time:.2f}s)")
        os.remove(temp_filename)
        
        text = response.text
        print("DEBUG: Raw text received (First 100 chars):", text[:100])
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        print("DEBUG: JSON block extracted. Parsing...")
            
        raw_data = json.loads(text)

        print("DEBUG: JSON parsed successfully. Running Logic Adapter...")

        result = organize_syllabus_data(raw_data)
        
        # Add Timing Info
        total_duration = time.time() - start_time
        result["analysis_duration_seconds"] = round(total_duration, 2)
        
        return result

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return {"error": str(e)}