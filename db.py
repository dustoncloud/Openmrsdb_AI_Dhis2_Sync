# ---------------------------------------------------------
# Bahmni AI + DHIS2 Sync Tool
# Copyright (c) 2025 [Deepak Neupane]
# Licensed under the MIT License (see LICENSE for details)
# ---------------------------------------------------------
# ================================
# File: db.py
# Purpose: Execute SQL safely on OpenMRS DB
# ================================

import os
import mysql.connector

# --------------------------------
# Database connection helper
# --------------------------------
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("OPENMRS_DB_HOST", "openmrsdb"),
        user=os.getenv("OPENMRS_DB_USERNAME", "openmrs-user"),
        password=os.getenv("OPENMRS_DB_PASSWORD", "password"),
        database=os.getenv("OPENMRS_DB_NAME", "openmrs"),
    )

# --------------------------------
# Public API used by app.py
# --------------------------------
def execute_sql(sql: str):
    """
    Executes SELECT SQL and returns rows as list of dicts
    """

    if not sql or not sql.strip():
        raise Exception("Empty SQL received for execution")

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        print("\n========== EXECUTING SQL ==========\n")
        print(sql)
        print("\n==================================\n")

        cursor.execute(sql)
        result = cursor.fetchall()

        return result

    except mysql.connector.Error as e:
        # This will return the specific DB error to the FastAPI console
        raise Exception(f"MySQL Error: {str(e)}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()