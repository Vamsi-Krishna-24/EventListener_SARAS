import sqlite3
import os

def execute_query(query,params=(),fetch = False):   #function FIRST
    connect = sqlite3.connect('C:/Users/karth/OneDrive/ドキュメント/Desktop/Final_Test/Dictionary.db')
    cursor = connect.cursor()
    cursor.execute(query,params)

    if fetch:
        result = cursor.fetchall()
        connect.close()
        return result
    
    connect.commit()
    connect.close()


def get_word_meaning(word):          #Function SECOND
    query='''
    SELECT definition, examples, synonm
    FROM dictionary
    WHERE word1 = ?
    '''

    result = execute_query(query, (word,),fetch = True)

    if result:
        definition, examples, synonm = result[0]
        return{
            'word':word,
            'definition':definition,
            'examples':examples.split(',') if examples else [],
            'synonyms':synonm.split(',') if synonm else []
        }
    else:
        return None