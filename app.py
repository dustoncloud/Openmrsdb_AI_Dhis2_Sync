# ---------------------------------------------------------
# Bahmni AI + DHIS2 Sync Tool
# Copyright (c) 2026 [Deepak Neupane]
# ---------------------------------------------------------
import os
import re
import json
import sqlite3
import requests
from datetime import datetime
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm import ask_llm
from prompt import build_prompt
from validator import validate_sql
from db import execute_sql 
from dhis2_mapping.dhis2_mapper import DHIS2Mapper

app = FastAPI()
mapper = DHIS2Mapper()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "sync_logs.json")
DB_PATH = os.path.join(BASE_DIR, "memory_store.db")

app.mount("/htmls", StaticFiles(directory="htmls"), name="htmls")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DHIS2_BASE_URL = "https://play.im.dhis2.org/stable-2-42-4/api/dataValueSets"

# --- Models ---
class QueryPayload(BaseModel):
    question: str
    start_date: str
    end_date: str

class SyncPayload(BaseModel):
    dhis_user: str
    dhis_pass: str
    data: list
    report_name: str
    period: str

class FeedbackPayload(BaseModel):
    question: str
    sql: str
    report_name: str

# --- Core Routes ---

@app.get("/index.html")
async def serve_index(): return FileResponse('index.html')

@app.get("/ai/sync/logs")
def get_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return []

@app.post("/ai/query")
def ai_query(payload: QueryPayload):
    user_q = payload.question.lower().strip()
    try:
        with open("schema.yaml") as f: schema = f.read()
    except: schema = ""

    full_prompt = build_prompt(schema, user_q, payload.start_date, payload.end_date)
    sql = ask_llm(full_prompt, question_text=user_q, start_date=payload.start_date, end_date=payload.end_date)
    
    if "SECURITY" in sql: return {"sql": sql, "data": [], "report_name": "SecurityAlert"}

    try:
        validate_sql(sql)
        data = execute_sql(sql)
    except Exception as e:
        return {"sql": sql, "data": [{"Error": str(e)}], "report_name": "Error"}
    
    if any(k in user_q for k in ["list", "grid", "patient", "name"]):
        report_name = "PatientGrid"
    elif any(k in user_q for k in ["weight", "vitals", "poids"]):
        report_name = "VitalsReport"
    else:
        report_name = "DailySummary"
    
    last_sync_info = None
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                logs = json.load(f)
                for log in logs:
                    if log.get("report") == report_name:
                        last_sync_info = log
                        break
            except: pass

    return {"sql": sql, "data": data, "report_name": report_name, "last_sync": last_sync_info}

# --- Sync Logic ---

@app.post("/ai/sync/dhis2")
def sync_to_dhis2(payload: SyncPayload):
    try:
        clean_period = re.sub(r'[^0-9]', '', payload.period)
        dhis_payload = mapper.transform(payload.data, period=clean_period, report_name=payload.report_name)
        
        if not dhis_payload or not dhis_payload.get("dataValues"):
            return {"status": "error", "message": "Mapping failed: No matching data elements found."}

        response = requests.post(
            f"{DHIS2_BASE_URL}?importStrategy=CREATE_AND_UPDATE&dryRun=false", 
            auth=(payload.dhis_user, payload.dhis_pass), 
            json=dhis_payload, 
            timeout=20
        )
        
        res_json = response.json()
        counts = res_json.get("response", {}).get("importCount", {})
        success = counts.get("imported", 0) + counts.get("updated", 0)

        if success > 0:
            new_log = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "period": payload.period,
                "report": payload.report_name,
                "count": success,
                "status": "Success"
            }
            logs = []
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r") as f:
                    content = f.read().strip()
                    if content: logs = json.loads(content)
            
            logs.insert(0, new_log)
            with open(LOG_FILE, "w") as f:
                json.dump(logs[:200], f, indent=4)

            return {"status": "completed", "message": f"Successfully synced {success} records."}
        else:
            return {"status": "warning", "message": "DHIS2 accepted request but 0 records changed."}
    except Exception as e:
        return {"status": "error", "message": f"Sync Error: {str(e)}"}

# --- Moderation & Learning Routes ---

@app.on_event("startup")
def setup_db():
    """Matches the exact schema from feedback_store.py"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback_loop (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            sql_query TEXT NOT NULL,
            report_name TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("✓ Moderation Database Initialized with sql_query column")

@app.post("/ai/feedback/suggest")
async def suggest_sql(data: dict):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Standardized to look for sql_query
        cursor.execute("SELECT status FROM feedback_loop WHERE question = ? AND sql_query = ?", 
                       (data['question'], data['sql']))
        existing = cursor.fetchone()
        
        if existing:
            status_text = "Approved" if existing[0] == 'approved' else "Pending"
            conn.close()
            return {"status": "exists", "message": f"Already {status_text}"}

        # Insert using standardized sql_query column
        cursor.execute("""
            INSERT INTO feedback_loop (question, sql_query, report_name, status) 
            VALUES (?, ?, ?, 'pending')
        """, (data['question'], data['sql'], data['report_name']))
        
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/ai/admin/review")
def get_pending_queries():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Fetching sql_query column to match DB
        cursor.execute("SELECT id, question, sql_query, report_name FROM feedback_loop WHERE status = 'pending'")
        rows = cursor.fetchall()
        conn.close()
        # We still return 'sql' as the key to the frontend to keep script.js happy
        return [{"id": r[0], "question": r[1], "sql": r[2], "report": r[3]} for r in rows]
    except Exception as e:
        print(f"Admin Review Error: {e}")
        return []

@app.post("/ai/admin/approve/{query_id}")
def approve_query(query_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE feedback_loop SET status = 'approved' WHERE id = ?", (query_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Approved."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@app.post("/ai/admin/delete/{query_id}")
def delete_query(query_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM feedback_loop WHERE id = ?", (query_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Query deleted successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}