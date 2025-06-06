import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "bdd_clients.db")

def get_connection():
    return sqlite3.connect(DB_PATH)
