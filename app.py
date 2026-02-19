# ---------------------------------------------------------
# Bahmni AI + DHIS2 Sync Tool
# Copyright (c) 2025 [Deepak Neupane]
# Licensed under the MIT License (see LICENSE for details)
# ---------------------------------------------------------
import os
import re
import json
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
print(f"DEBUG: Logs will be stored at: {LOG_FILE}")

app.mount("/htmls", StaticFiles(directory="htmls"), name="htmls")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DHIS2_BASE_URL = "https://play.im.dhis2.org/stable-2-42-4/api/dataValueSets"

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

@app.get("/")
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
    
    # Logic to determine Report Name
    if any(k in user_q for k in ["list", "grid", "patient", "name"]):
        report_name = "PatientGrid"
    elif any(k in user_q for k in ["weight", "vitals", "poids"]):
        report_name = "VitalsReport"
    else:
        report_name = "DailySummary"
    
    #  NEW: Contextual Log Checking 
    last_sync_info = None
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                logs = json.load(f)
                # Find the first entry that matches this specific report_name
                for log in logs:
                    if log.get("report") == report_name:
                        last_sync_info = log
                        break
            except:
                pass

    return {
        "sql": sql, 
        "data": data, 
        "report_name": report_name,
        "last_sync": last_sync_info # This tells the UI when this specific report was last sent
    }

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
            
            #  ROBUST WRITE LOGIC 
            logs = []
            try:
                if os.path.exists(LOG_FILE):
                    with open(LOG_FILE, "r") as f:
                        content = f.read().strip()
                        if content: # Only load if file isn't empty
                            logs = json.loads(content)
                
                # Insert at top, trim to 200
                logs.insert(0, new_log)
                logs = logs[:200]
                
                with open(LOG_FILE, "w") as f:
                    json.dump(logs, f, indent=4)
                
                print(f"LOG SUCCESS: Written to {LOG_FILE}")
            except Exception as log_err:
                print(f"LOG ERROR: Could not write to file: {log_err}")

            return {"status": "completed", "message": f"Successfully synced {success} records."}
        else:
            conflicts = res_json.get("response", {}).get("importCount", {}) # or res_json.get("conflicts")
            return {"status": "warning", "message": "DHIS2 accepted the request but 0 records were changed (likely duplicate data)."}
            
    except Exception as e:
        return {"status": "error", "message": f"Sync Error: {str(e)}"}