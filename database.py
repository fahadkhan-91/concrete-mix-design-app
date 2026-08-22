import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "mix_designs.db")


def init_db():
    # agar table pehle se nahi hai to bana do
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            inputs_json TEXT NOT NULL,
            results_json TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_project(name, inputs, results):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO projects (name, inputs_json, results_json) VALUES (?, ?, ?)",
        (name, json.dumps(inputs), json.dumps(results))
    )
    conn.commit()
    conn.close()


def get_all_projects():
    # sirf id, name aur date list mein dikhane ke liye
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_at FROM projects ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_project(project_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT inputs_json, results_json FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0]), json.loads(row[1])
    return None, None


def delete_project(project_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()


def search_projects(keyword):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, created_at FROM projects WHERE name LIKE ? ORDER BY created_at DESC",
        (f"%{keyword}%",)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows
