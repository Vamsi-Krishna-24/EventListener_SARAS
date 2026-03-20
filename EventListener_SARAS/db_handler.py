import sqlite3
import os
import sys

# ───────────────────────────────────────────────
# DICTIONARY DB  — stays in install directory (read-only bundled content)
# ───────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "Dictionary.db")


def execute_query(query,params=(),fetch = False):  
    connect = sqlite3.connect(DB_PATH)
    cursor = connect.cursor()
    cursor.execute(query,params)

    if fetch:
        result = cursor.fetchall()
        connect.close()
        return result
    
    connect.commit()
    connect.close()


def get_word_meaning(word: str):
    if not word or not word.strip():
        print("[DB] Empty word skipped", flush=True)
        return None

    query = '''
        SELECT definition, examples, synonm
        FROM Dictionary
        WHERE word1 = ?
    '''

    try:
        result = execute_query(query, (word.lower(),), fetch=True)
        
        if result and len(result) > 0:
            definition, examples_str, synonyms_str = result[0]
            
            examples = examples_str.split(',') if examples_str else []
            synonyms = synonyms_str.split(',') if synonyms_str else []
            
            return {
                'word': word,
                'definition': definition or "No definition available",
                'examples': [ex.strip() for ex in examples if ex.strip()],
                'synonyms': [syn.strip() for syn in synonyms if syn.strip()]
            }
        
        print(f"[DB] Word '{word}' not found in 'words' table")
        return None
    
    except sqlite3.Error as e:
        print(f"[DB] Lookup failed for '{word}': {e}", flush=True)
        return None


# ───────────────────────────────────────────────
# PROFILE DB  — lives in AppData\Roaming\SARAS\
#               survives app uninstall/reinstall
# ───────────────────────────────────────────────
def get_profile_db_path():
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    profile_dir = os.path.join(appdata, 'SARAS')
    os.makedirs(profile_dir, exist_ok=True)
    return os.path.join(profile_dir, 'profile.db')


PROFILE_DB_PATH = get_profile_db_path()


def init_profile_db():
    """Creates the user_profile table if it doesn't already exist."""
    connect = sqlite3.connect(PROFILE_DB_PATH)
    cursor = connect.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profile (
            id            INTEGER PRIMARY KEY,
            first_name    TEXT NOT NULL,
            last_name     TEXT NOT NULL,
            email         TEXT NOT NULL,
            license_key   TEXT NOT NULL,
            activated_at  TEXT NOT NULL
        )
    ''')
    connect.commit()
    connect.close()
    print("[DB] Profile DB initialised", flush=True)


def save_user_profile(first_name: str, last_name: str, email: str, license_key: str):
    """Writes the user profile after successful activation. Called once ever."""
    from datetime import datetime
    activated_at = datetime.utcnow().isoformat()

    connect = sqlite3.connect(PROFILE_DB_PATH)
    cursor = connect.cursor()
    cursor.execute('''
        INSERT INTO user_profile (first_name, last_name, email, license_key, activated_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (first_name, last_name, email, license_key, activated_at))
    connect.commit()
    connect.close()
    print(f"[DB] Profile saved for {first_name} {last_name}", flush=True)


def get_user_profile():
    """Returns the stored user profile dict, or None if not activated yet."""
    try:
        connect = sqlite3.connect(PROFILE_DB_PATH)
        cursor = connect.cursor()
        cursor.execute('''
            SELECT first_name, last_name, email, license_key, activated_at
            FROM user_profile
            LIMIT 1
        ''')
        row = cursor.fetchone()
        connect.close()

        if row:
            return {
                'first_name':   row[0],
                'last_name':    row[1],
                'email':        row[2],
                'license_key':  row[3],
                'activated_at': row[4],
            }
        return None

    except sqlite3.Error as e:
        print(f"[DB] Could not read profile: {e}", flush=True)
        return None


def is_activated():
    """Returns True if a user profile already exists locally."""
    profile = get_user_profile()
    return profile is not None