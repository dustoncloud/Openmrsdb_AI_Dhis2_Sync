# ---------------------------------------------------------
# Bahmni AI + DHIS2 Sync Tool
# Copyright (c) 2026 [Deepak Neupane]
# ---------------------------------------------------------
import sqlite3
import os
from datetime import datetime

# Path to your moderation database
DB_PATH = "memory_store.db"

def get_approved_memory():
    """
    Fetches the 5 most recent approved queries to serve as 'Few-Shot' 
    examples for the AI. This is how the AI 'learns'.
    """
    if not os.path.exists(DB_PATH):
        return ""

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Fetch approved items. We map 'question' and 'sql' to show the AI how to behave.
        cursor.execute("""
            SELECT question, sql 
            FROM feedback_loop 
            WHERE status = 'approved' 
            ORDER BY id DESC LIMIT 5
        """)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return ""

        memory_segment = "\n## PREVIOUSLY APPROVED EXAMPLES (LEARNED BEHAVIOR):\n"
        for q, sql in rows:
            memory_segment += f"User: \"{q}\"\nSQL: {sql}\n\n"
        return memory_segment
    except Exception as e:
        print(f"Memory Fetch Error: {e}")
        return ""

def build_prompt(schema: str, question: str, start_date: str = None, end_date: str = None) -> str:
    """
    Constructs a high-precision system prompt for Bahmni/OpenMRS SQL generation.
    Now includes a 'Memory' section that pulls from the approved database.
    """
    
    # Fallback dynamic dates
    now = datetime.now()
    current_date = now.strftime('%Y-%m-%d')
    
    # UI Context
    if start_date and end_date:
        ui_context = f"\nCRITICAL: The user's UI is currently filtered between '{start_date}' and '{end_date}'. ALL queries must strictly include `AND DATE(...) BETWEEN '{start_date}' AND '{end_date}'` unless the user explicitly asks for 'all time'."
    else:
        ui_context = f"\nNo UI date filter applied. Assume current date context: Today is {current_date}."

    # Fetch Learned Examples from DB
    learned_memory = get_approved_memory()

    system_instruction = f"""
You are a Senior SQL Engineer for the Bahmni/OpenMRS Hospital System.
Your goal is to generate clean, executable MySQL queries.

## DATABASE SCHEMA CONTEXT:
{schema}

## UI AND TIME CONTEXT:{ui_context}

## PRODUCTION RULES (STRICT):
1. Readable Names: Always JOIN `person_name` (pn) to `person` (pe) to return `pn.given_name` and `pn.family_name`.
2. Never Hardcode IDs: Join metadata tables (encounter_type, concept_name) and use LIKE filters.
3. The EAV Model: For vitals/clinical data, use the `obs` table. Join `concept_name` for both keys and values.
4. Data Integrity: Always include `voided = 0` for EVERY table queried.
5. Output: Return ONLY the raw SQL. No markdown, no explanations.

{learned_memory}

## BASELINE EXAMPLES:
User: "How many patients registered?"
SQL: SELECT COUNT(*) FROM person pe WHERE pe.voided = 0 AND DATE(pe.date_created) BETWEEN '{start_date}' AND '{end_date}';

## ACTUAL USER QUESTION:
"{question}"

## SQL:
"""
    return system_instruction