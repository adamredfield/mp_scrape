import pandas as pd
import os
import sys
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.database.utils import create_connection
data_path = os.path.join(project_root, 'src', 'data', 'TagMapping_202412131658.csv')

# Read CSV
df = pd.read_csv(data_path)

# Insert into Neon
with create_connection() as conn:
    cursor = conn.cursor()
    
    for _, row in df.iterrows():
        insert_date = datetime.now() if pd.isna(row['insert_date']) else pd.to_datetime(row['insert_date'])

        cursor.execute("""
            INSERT INTO analysis.TagMapping_migration (
                raw_tag, 
                clean_tag, 
                original_tag_type, 
                mapped_tag_type, 
                is_active, 
                insert_date
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (raw_tag, original_tag_type) DO NOTHING
        """, (
            row['raw_tag'],
            row['clean_tag'],
            row['original_tag_type'],
            row['mapped_tag_type'],
            bool(row['is_active']),
            insert_date
        ))
    
    conn.commit()