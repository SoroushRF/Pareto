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
import zipfile
import io
from docx import Document
from PIL import Image # Part of Pillow library
from prompts.system_prompt import system_prompt


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

def process_docx(file_path):
    """
    Deep Extraction for .docx:
    1. Uses python-docx to read text/tables.
    2. Uses zipfile to extract embedded images (e.g. screenshots of tables).
    """
    content_parts = []
    
    # A. Extract Text
    try:
        doc = Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                # Join cells with pipe to simulate table structure
                row_data = [cell.text for cell in row.cells]
                full_text.append(" | ".join(row_data))
        
        text_content = "\n".join(full_text)
        if text_content.strip():
            content_parts.append(text_content)
            print("DEBUG: Extracted text from DOCX.")
    except Exception as e:
        print(f"Warning: Failed to extract text from DOCX: {e}")

    # B. Extract Images (Treating .docx as a ZIP archive)
    try:
        with zipfile.ZipFile(file_path) as z:
            # Look for image files inside the internal structure
            all_files = z.namelist()
            media_files = [f for f in all_files if f.startswith('word/media/')]
            
            for media_path in media_files:
                image_data = z.read(media_path)
                image = Image.open(io.BytesIO(image_data))
                content_parts.append(image)
                print(f"DEBUG: Extracted image: {media_path}")
                
    except Exception as e:
        print(f"Warning: Failed to extract images from DOCX: {e}")
        
    return content_parts

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

       # 2. Prepare Content (Switch between DOCX and Standard)
        gemini_content = [system_prompt]

        if file.filename.lower().endswith(".docx"):
            print("DEBUG: Detected DOCX. Running Deep Extraction...")
            # This calls the helper function (process_docx) you added in Phase 2
            docx_parts = process_docx(temp_filename)
            if not docx_parts:
                raise Exception("Failed to extract content (text or images) from DOCX.")
            gemini_content.extend(docx_parts)
        else:
            # Standard Path (PDF, Images, Text)
            print(f"DEBUG: Uploading {temp_filename} to Gemini...")
            uploaded_file = genai.upload_file(temp_filename)
            gemini_content.append(uploaded_file)

        print(f"DEBUG: Prep complete ({time.time() - start_time:.2f}s). Starting Generation...")
        
        # 3. Generate with Streaming
        # We pass 'gemini_content' (which now holds Prompt + File/Parts)
        response_stream = await model.generate_content_async(
            gemini_content, 
            stream=True
        )
        # 3. Build Response Chunk by Chunk + MONITOR CONNECTION
        full_text = ""
# ... inside analyze_syllabus ...
        
        print(f"DEBUG: Streaming response...")
        
        async for chunk in response_stream:
            # 1. Pulse Check (Cancellation)
            if await request.is_disconnected():
                print(f"🛑 OPERATION ABORTED: User disconnected at {time.time() - start_time:.2f}s")
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
                return 

            # 2. Safe Text Extraction (The Fix)
            try:
                # Only add text if the chunk actually contains text parts
                if chunk.parts:
                    full_text += chunk.text
            except Exception as chunk_error:
                # If a chunk is empty/metadata-only, ignore it and keep going
                continue
        
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

        # Calculate final duration
        elapsed = round(time.time() - start_time, 2)
        
        # Get organized data
        result = organize_syllabus_data(raw_data)
        
        # Inject duration
        result["analysis_duration"] = elapsed
        
        return result

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return {"error": str(e)}