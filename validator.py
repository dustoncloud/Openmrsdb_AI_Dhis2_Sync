# =====================================================================
# SQL SECURITY VALIDATOR MODULE#
# =====================================================================
# Developed by: Deepak Neupane
# Copyright:    (c) 2025 Deepak Neupane
# License:      MIT
# Function:     Validates LLM-generated SQL against a strict whitelist 
#               to prevent SQL Injection and unauthorized data access.
# =====================================================================

FORBIDDEN = ["insert", "update", "delete", "drop", "alter"]

def validate_sql(sql):
    sql_lower = sql.lower()
    
    for word in FORBIDDEN:
        if word in sql_lower:
            raise Exception("Unsafe SQL detected")

    if not sql_lower.strip().startswith("select"):
        raise Exception("Only SELECT queries allowed")

    return True
