# ---------------------------------------------------------
# Bahmni AI + DHIS2 Sync Tool
# Copyright (c) 2025 [Deepak Neupane]
# Licensed under the MIT License (see LICENSE for details)
# ---------------------------------------------------------
import sqlite3
import os

DB_PATH = "memory_store.db"

def init_db():
    """Creates the database and table if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback_loop (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            sql_query TEXT NOT NULL,
            report_name TEXT,
            status TEXT DEFAULT 'approved',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_successful_query(question, sql, report_name):
    """Saves a verified SQL query to help the AI learn."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO feedback_loop (question, sql_query, report_name) VALUES (?, ?, ?)",
        (question.lower().strip(), sql, report_name)
    )
    conn.commit()
    conn.close()

def get_learned_examples(limit=5):
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # CRITICAL CHANGE: Only fetch 'approved' status
    cursor.execute("""
        SELECT question, sql_query 
        FROM feedback_loop 
        WHERE status = 'approved' 
        ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# Initialize the database immediately when this module is imported
init_db()
