import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import src.scraping.helper_functions as helper_functions

total_pages = helper_functions.get_total_pages()
print(f"Total pages: {total_pages}")