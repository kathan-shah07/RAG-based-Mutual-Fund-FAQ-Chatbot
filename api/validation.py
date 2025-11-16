"""
Validation functions for user input.
Validates PII detection and comparison question restrictions.
"""
import re
from typing import Optional, Dict, Any


def contains_pii(text: str) -> Optional[str]:
    """
    Check if text contains Personally Identifiable Information (PII).
    
    Args:
        text: Text to check for PII
        
    Returns:
        Type of PII found (e.g., 'PAN card number') or None if no PII detected
    """
    if not text:
        return None
    
    # PAN card pattern: 5 letters, 4 digits, 1 letter (e.g., ABCDE1234F)
    pan_pattern = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', re.IGNORECASE)
    if pan_pattern.search(text):
        return 'PAN card number'
    
    # Aadhaar pattern: 12 digits, possibly with spaces or hyphens (e.g., 1234 5678 9012)
    aadhaar_pattern = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
    if aadhaar_pattern.search(text):
        return 'Aadhaar number'
    
    # Account number patterns: 9-18 digits with account-related keywords
    account_pattern = re.compile(r'\b\d{9,18}\b')
    account_keywords = re.compile(r'(account|acc|a/c|ac no|account number|account no)', re.IGNORECASE)
    if account_pattern.search(text) and account_keywords.search(text):
        return 'Account number'
    
    # OTP pattern: 4-8 digit codes, often with "OTP" keyword
    otp_pattern = re.compile(r'\b(otp|one.?time.?password)[\s:]*\d{4,8}\b', re.IGNORECASE)
    if otp_pattern.search(text):
        return 'OTP'
    
    # Email pattern
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    if email_pattern.search(text):
        return 'Email address'
    
    # Phone number patterns: Indian formats (10 digits, with or without country code)
    # Matches: +91-1234567890, 91-1234567890, 01234567890, 1234567890, etc.
    phone_pattern = re.compile(r'\b(\+?91[\s-]?)?[6-9]\d{9}\b')
    if phone_pattern.search(text):
        # Exclude common non-phone numbers (years, amounts, etc.)
        year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        amount_pattern = re.compile(r'₹|rs\.?|rupees?', re.IGNORECASE)
        if not year_pattern.search(text) and not amount_pattern.search(text):
            return 'Phone number'
    
    return None


def validate_comparison(question: str) -> Dict[str, Any]:
    """
    Validate comparison questions to ensure they only compare factual parameters.
    
    Args:
        question: User's question
        
    Returns:
        Dictionary with 'valid' (bool) and optional 'reason' (str) for rejection
    """
    if not question:
        return {'valid': True}
    
    lower_question = question.lower()
    
    # Check if it's a comparison question
    comparison_keywords = [
        'compare', 'comparison', 'vs', 'versus', 'better', 'best',
        'which is better', 'which one is better', 'difference between',
        'differences', 'which should', 'should i choose', 'recommend'
    ]
    
    is_comparison = any(keyword in lower_question for keyword in comparison_keywords)
    
    if not is_comparison:
        return {'valid': True}
    
    # Check for disallowed comparison types
    disallowed_keywords = [
        'performance', 'returns', 'return', 'roi', 'profit', 'loss',
        'gain', 'growth', 'appreciation', 'depreciation', 'yield',
        'better', 'best', 'worst', 'should i', 'recommend', 'advice',
        'suggest', 'opinion', 'which is better', 'which one is better'
    ]
    
    has_disallowed = any(keyword in lower_question for keyword in disallowed_keywords)
    
    if has_disallowed:
        return {
            'valid': False,
            'reason': 'I can only compare mutual funds on factual parameters like expense ratio, lock-in period, benchmark, or portfolio mix. I cannot compare performance, returns, or provide recommendations on which fund is better.'
        }
    
    # Check for allowed factual comparison parameters
    allowed_keywords = [
        'expense ratio', 'lock-in', 'lock in', 'benchmark', 'portfolio mix',
        'fund category', 'fund type', 'risk level', 'minimum investment',
        'minimum sip', 'exit load', 'fund manager', 'fund house'
    ]
    
    has_allowed = any(keyword in lower_question for keyword in allowed_keywords)
    
    if not has_allowed:
        return {
            'valid': False,
            'reason': 'I can only compare mutual funds on factual parameters like expense ratio, lock-in period, benchmark, or portfolio mix. Please specify which factual parameters you want to compare.'
        }
    
    return {'valid': True}

