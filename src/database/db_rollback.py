import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.database.utils import create_connection

connection = create_connection()
cursor = connection.cursor()

 # Write the SQL command to create the Students table
drop_table_query = '''
DROP TABLE IF EXISTS Routes;
DROP TABLE IF EXISTS RouteComments;
DROP TABLE IF EXISTS RouteAnalysis;
'''

cursor.executescript(drop_table_query)
connection.commit()
connection.close()