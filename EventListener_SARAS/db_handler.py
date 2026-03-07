import sqlite3
import os
import sys

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

    # Clean SQL - no # comments inside triple quotes
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