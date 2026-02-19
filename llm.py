# ---------------------------------------------------------
# Bahmni AI + DHIS2 Sync Tool
# Copyright (c) 2025 [Deepak Neupane]
# Licensed under the MIT License (see LICENSE for details)
# ---------------------------------------------------------
import os
import re

#  CONFIGURATION 
SQL_FOLDER = os.path.join(os.path.dirname(__file__), "queries")
if not os.path.exists(SQL_FOLDER):
    os.makedirs(SQL_FOLDER)

MANUAL_REPORTS = {
    "101": "Active IPD/Admissions List",
    "102": "Program Enrollment (HIV/TB/MCH)",
    "103": "Laboratory Results (EAV Model)",
    "104": "Patient Registration & Address Details",
    "105": "Pharmacy Medication Orders"
}

OPENMRS_CONTEXT = """
You are an expert OpenMRS and Bahmni MySQL Analyst.
SCHEMA GUIDELINES:
1. PATIENTS: `person` -> `patient`. Names in `person_name`. MRN in `patient_identifier`.
2. CLINICAL: `visit` (Admissions), `encounter` (Clinical events).
3. BAHMNI/IPD: Admitted patients have a `visit` where `date_stopped` is NULL.
4. OBSERVATIONS: `obs` table. Join `concept_name` to find questions. 
   Answers are in `value_numeric`, `value_text`, or `value_coded` (join `concept_name` again for labels).
5. PROGRAMS: `patient_program` links patients to `program` names.
6. DRUGS: `orders` -> `drug_order` -> `drug`.
RULES: Use standard joins. Always filter `voided = 0`. Output RAW SQL ONLY.
"""

def ask_llm(prompt_text: str, question_text: str, start_date=None, end_date=None) -> str:
    clean_q = question_text.lower().strip()

    #  1. SECURITY CHECK 
    if any(cmd in clean_q for cmd in ["drop ", "delete ", "truncate ", "update ", "alter ", "insert "]):
        return "SELECT 'SECURITY WARNING: Action blocked' as message;"

    #  2. MENU MODE 
    if clean_q in ["list", "help", "menu", "manual"]:
        menu_items = [f"SELECT '{k}' as Code, '{v}' as Report" for k, v in MANUAL_REPORTS.items()]
        return " UNION ALL ".join(menu_items)

    #  3. MANUAL SWITCH MODE (Numbers 101, 102...) 
    match = re.match(r"^(?:sql\s+)?(\d+)$", clean_q)
    if match:
        query_id = match.group(1)
        file_path = os.path.join(SQL_FOLDER, f"{query_id}.sql")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                raw_sql = f.read().strip()
                # Strips comments and semicolons to prevent "Only SELECT allowed" errors
                clean_sql = re.sub(r'(--.*)|(/\*[\s\S]*?\*/)', '', raw_sql).strip()
                if clean_sql.endswith(";"): clean_sql = clean_sql[:-1]
                return clean_sql.replace("{start_date}", str(start_date)).replace("{end_date}", str(end_date))
        return f"SELECT 'Error: File {query_id}.sql not found' as message;"

    #  4. AI PATH (Online Only) 
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and api_key.startswith("sk-"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": OPENMRS_CONTEXT},
                    {"role": "user", "content": f"Date range: {start_date} to {end_date}. Query: {prompt_text}"}
                ],
                temperature=0
            )
            return response.choices[0].message.content.strip().replace("```sql", "").replace("```", "").split(';')[0]
        except:
            pass 

    #  5. SMART ROUTER (OFFLINE ROBUST LOGIC)
    
    # Pre-formatted date filters for the OpenMRS schema
    d_pe = f"AND DATE(pe.date_created) BETWEEN '{start_date}' AND '{end_date}'"
    d_e = f"AND DATE(e.encounter_datetime) BETWEEN '{start_date}' AND '{end_date}'"

    # A. Total Persons (All Time)
    if "total persons" in clean_q:
        return "SELECT COUNT(*) as Total_Persons_In_System FROM person WHERE voided = 0"

    # B. Monthly Growth
    if "growth" in clean_q:
        return """
        SELECT DATE_FORMAT(date_created, '%Y-%m') as Month, COUNT(*) as New_Registrations 
        FROM person 
        WHERE voided = 0 
        GROUP BY Month 
        ORDER BY Month DESC LIMIT 12
        """

    # C. Registration Count (In Date Range)
    if "registered" in clean_q or "registration count" in clean_q:
        return f"""
        SELECT COUNT(*) as Registrations_In_Period 
        FROM person pe 
        WHERE voided = 0 {d_pe}
        """

    # D. Appointments / RDVs (Using Encounters as a proxy for visits)
    if "appointment" in clean_q or "rdv" in clean_q:
        return f"""
        SELECT pn.given_name as First_Name, pn.family_name as Last_Name, 
               e.encounter_datetime as Visit_Date, et.name as Visit_Type 
        FROM encounter e 
        JOIN encounter_type et ON e.encounter_type = et.encounter_type_id 
        JOIN person_name pn ON e.patient_id = pn.person_id 
        WHERE e.voided = 0 {d_e} 
        ORDER BY e.encounter_datetime DESC LIMIT 50
        """

    # E. ANC Report (Antenatal Care - Advanced EAV Handling)
    if "anc" in clean_q:
        return f"""
        SELECT 
            pn.given_name as First_Name, 
            pn.family_name as Last_Name, 
            DATE(e.encounter_datetime) as Date, 
            cn_question.name as ANC_Observation, 
            COALESCE(o.value_numeric, o.value_text, cn_answer.name) as Result
        FROM obs o 
        JOIN encounter e ON o.encounter_id = e.encounter_id
        JOIN person_name pn ON e.patient_id = pn.person_id 
        -- Join to get the Question Name (e.g., Gravida, Parity)
        JOIN concept_name cn_question ON o.concept_id = cn_question.concept_id 
             AND cn_question.concept_name_type = 'FULLY_SPECIFIED' 
             AND cn_question.locale = 'en'
        -- Left join to get the Answer Name if it was a coded dropdown
        LEFT JOIN concept_name cn_answer ON o.value_coded = cn_answer.concept_id 
             AND cn_answer.concept_name_type = 'FULLY_SPECIFIED' 
             AND cn_answer.locale = 'en'
        WHERE o.voided = 0 
        AND (
            cn_question.name LIKE '%ANC%' 
            OR cn_question.name LIKE '%Pregnancy%' 
            OR cn_question.name LIKE '%Gravida%' 
            OR cn_question.name LIKE '%Parity%' 
            OR cn_question.name LIKE '%Estimated date of confinement%'
        )
        {d_e}
        ORDER BY e.encounter_datetime DESC LIMIT 50
        """

    # F. Vitals Summary (Pivot Table for cleaner UI display)
    if "vitals" in clean_q:
        return f"""
        SELECT 
            pn.given_name as First_Name, 
            pn.family_name as Last_Name, 
            DATE(e.encounter_datetime) as Date,
            MAX(CASE WHEN cn.name LIKE '%Weight%' THEN o.value_numeric END) as Weight_KG,
            MAX(CASE WHEN cn.name LIKE '%Height%' THEN o.value_numeric END) as Height_CM,
            MAX(CASE WHEN cn.name LIKE '%Systolic%' THEN o.value_numeric END) as BP_Systolic,
            MAX(CASE WHEN cn.name LIKE '%Diastolic%' THEN o.value_numeric END) as BP_Diastolic
        FROM obs o 
        JOIN encounter e ON o.encounter_id = e.encounter_id
        JOIN concept_name cn ON o.concept_id = cn.concept_id
        JOIN person_name pn ON e.patient_id = pn.person_id
        WHERE o.voided = 0 {d_e} 
        GROUP BY e.encounter_id, pn.given_name, pn.family_name, DATE(e.encounter_datetime)
        -- Only show rows where at least one vital was actually recorded
        HAVING Weight_KG IS NOT NULL OR BP_Systolic IS NOT NULL
        ORDER BY Date DESC LIMIT 50
        """

    #  6. FINAL FALLBACK 
    return f"SELECT 'Mode: Offline Fallback' as Status, COUNT(*) as Total_Active_Patients FROM patient WHERE voided = 0"