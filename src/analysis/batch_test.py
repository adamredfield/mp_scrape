from src.analysis.batch_ai_analysis import process_batch_results
import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)


batch_id = "batch_6775ad1607208190b55203a5523a3195"
process_batch_results(batch_id)
