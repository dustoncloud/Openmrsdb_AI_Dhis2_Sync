# ---------------------------------------------------------
# Bahmni AI + DHIS2 Sync Tool
# Copyright (c) 2026 [Deepak Neupane]
# Licensed under the MIT License (see LICENSE for details)
# ---------------------------------------------------------
import os
import re

#  CONFIGURATION 
SQL_FOLDER = os.path.join(os.path.dirname(__file__), "queries")
if not os.path.exists(SQL_FOLDER):
    os.makedirs(SQL_FOLDER)

# Pre-defined manual report list
MANUAL_REPORTS = {
    "101": "Active IPD/Admissions",
    "102": "Program Enrollment (HIV/TB/MCH)",
    "103": "Laboratory Results (EAV)",
    "104": "Patient Registration Details",
    "105": "Pharmacy Medication Orders"
}

def ask_llm(prompt_text: str, question_text: str, start_date=None, end_date=None) -> str:
    clean_q = question_text.lower().strip()

    # --- 1. SECURITY CHECK ---
    if any(cmd in clean_q for cmd in ["drop ", "delete ", "truncate ", "update ", "alter "]):
        return "SELECT 'SECURITY WARNING: Action blocked' as message;"

    # --- 2. MENU MODE ---
    if clean_q in ["list", "help", "menu", "manual"]:
        menu_items = [f"SELECT '{k}' as Code, '{v}' as Report" for k, v in MANUAL_REPORTS.items()]
        return " UNION ALL ".join(menu_items)

    # --- 3. MANUAL FILE LOOKUP (101.sql, etc) ---
    match = re.match(r"^(?:sql\s+)?(\d+)$", clean_q)
    if match:
        query_id = match.group(1)
        file_path = os.path.join(SQL_FOLDER, f"{query_id}.sql")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                raw_sql = f.read().strip()
                clean_sql = re.sub(r'(--.*)|(/\*[\s\S]*?\*/)', '', raw_sql).strip()
                if clean_sql.endswith(";"): clean_sql = clean_sql[:-1]
                return clean_sql.replace("{start_date}", str(start_date)).replace("{end_date}", str(end_date))
        return f"SELECT 'Error: File {query_id}.sql not found' as message;"

    # --- 4. AI PATH (LOCAL OLLAMA PRODUCTION) ---
    api_key = os.getenv("OPENAI_API_KEY", "ollama") 
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1") 
    model_name = os.getenv("LLM_MODEL", "qwen2.5-coder:7b") 

    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": prompt_text},
                    {"role": "user", "content": f"Dates: {start_date} to {end_date}. Query: {question_text}"}
                ],
                temperature=0
            )
            sql = response.choices[0].message.content.strip()
            return re.sub(r'```sql|```', '', sql).strip().split(';')[0]
        except Exception as e:
            print(f"Local AI Offline: {e}")
            pass 

    # --- 5. FULL OFFLINE ROUTER (RESTORED & IMPROVED) ---
    # Based on your Schema Rules
    d_filt = f"BETWEEN '{start_date}' AND '{end_date}'"

    # A. Active IPD (Schema Rule: date_stopped IS NULL)
    if any(k in clean_q for k in ["admitted", "ipd", "staying"]):
        return f"""
        SELECT pi.identifier, pn.given_name, v.date_started 
        FROM visit v
        JOIN person_name pn ON v.patient_id = pn.person_id
        JOIN patient_identifier pi ON v.patient_id = pi.patient_id
        WHERE v.date_stopped IS NULL AND v.voided = 0
        """

    # B. Monthly Growth Logic
    if "growth" in clean_q or "monthly" in clean_q:
        return """
        SELECT DATE_FORMAT(date_created, '%Y-%m') as Month, COUNT(*) as New_Registrations 
        FROM person WHERE voided = 0 GROUP BY Month ORDER BY Month DESC LIMIT 12
        """

    # C. Pharmacy/Medications (Schema: drug_order + orders)
    if "drug" in clean_q or "medication" in clean_q or "pharmacy" in clean_q:
        return f"""
        SELECT pn.given_name, cn.name as Drug, do.dose, do.frequency, o.date_activated
        FROM drug_order do
        JOIN orders o ON do.order_id = o.order_id
        JOIN concept_name cn ON o.concept_id = cn.concept_id
        JOIN person_name pn ON o.patient_id = pn.person_id
        WHERE o.voided = 0 AND DATE(o.date_activated) {d_filt}
        """

    # D. ANC / Clinical Observations (Schema: obs + concept_name)
    if "anc" in clean_q or "observation" in clean_q:
        return f"""
        SELECT pn.given_name, DATE(o.obs_datetime) as Date, cn.name as Question, 
               COALESCE(o.value_numeric, o.value_text, cn_ans.name) as Answer
        FROM obs o
        JOIN concept_name cn ON o.concept_id = cn.concept_id
        LEFT JOIN concept_name cn_ans ON o.value_coded = cn_ans.concept_id
        JOIN person_name pn ON o.person_id = pn.person_id
        WHERE o.voided = 0 AND (cn.name LIKE '%ANC%' OR cn.name LIKE '%Pregnancy%')
        AND DATE(o.obs_datetime) {d_filt}
        """

    # E. Registration Count
    if "registered" in clean_q or "total patient" in clean_q:
        return f"SELECT COUNT(*) as Registrations FROM person WHERE voided = 0 AND DATE(date_created) {d_filt}"

    # F. Diagnosis (Schema: diagnosis table)
    if "diagnosis" in clean_q:
        return f"""
        SELECT pn.given_name, d.diagnosis_label, d.certainty
        FROM diagnosis d
        JOIN person_name pn ON d.patient_id = pn.person_id
        WHERE d.voided = 0 AND DATE(d.date_created) {d_filt}
        """

    # FINAL FALLBACK
    return f"SELECT 'Fallback' as Status, COUNT(*) as Active_Patients FROM patient WHERE voided = 0"