import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import pytest
from src.analysis.analysis_utils import get_grade_group

def test_single_digit_grades():
    assert get_grade_group('5.9', 'base') == '5.9'
    assert get_grade_group('5.8', 'base') == '5.8'
    assert get_grade_group('5.7', 'base') == '5.7'

def test_double_digit_grades():
    assert get_grade_group('5.10', 'base') == '5.10'
    assert get_grade_group('5.11', 'base') == '5.11'
    assert get_grade_group('5.12', 'base') == '5.12'

def test_grades_with_suffixes():
    # Testing minus grades
    assert get_grade_group('5.10a', 'granular') == '5.10-'
    assert get_grade_group('5.11b', 'granular') == '5.11-'
    assert get_grade_group('5.12-', 'granular') == '5.12-'
    
    # Testing plus grades
    assert get_grade_group('5.10d', 'granular') == '5.10+'
    assert get_grade_group('5.11c', 'granular') == '5.11+'
    assert get_grade_group('5.9+', 'granular') == '5.9+'

def test_non_yds_grades():
    """Test grades that don't start with '5.'"""
    assert get_grade_group('V4', 'base') == 'V4'
    assert get_grade_group('WI3', 'granular') == 'WI3'
    assert get_grade_group('M5', 'base') == 'M5'

def test_default_level():
    """Test default level parameter (base)"""
    assert get_grade_group('5.10a') == '5.10'
    assert get_grade_group('5.9+') == '5.9'
    assert get_grade_group('5.11d') == '5.11'

def test_no_level():
    """Test when level is neither base nor granular"""
    assert get_grade_group('5.10a', 'original') == '5.10a'
    assert get_grade_group('5.11d', 'full') == '5.11d'
    assert get_grade_group('5.9+', 'other') == '5.9+'

def test_edge_cases():
    """Test edge cases and potential problem inputs"""
    
    # Malformed grades
    assert get_grade_group('5.10x', 'granular') == '5.10'
    assert get_grade_group('5.9/', 'base') == '5.9'

    # Empty or None inputs
    assert get_grade_group(None) is None
    assert get_grade_group('') is None

if __name__ == '__main__':
    pytest.main(['-v', __file__]) 