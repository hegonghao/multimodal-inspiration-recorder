"""
Helper Utility Functions
辅助工具函数集合
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from uuid import uuid4


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize text by removing dangerous characters
    
    Args:
        text: Input text to sanitize
        max_length: Optional maximum length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove null bytes
    sanitized = text.replace('\x00', '')
    
    # Normalize whitespace
    sanitized = ' '.join(sanitized.split())
    
    # Truncate if needed
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip() + "..."
    
    return sanitized


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to specified length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rstrip() + suffix


def format_timestamp(dt: datetime, format: str = "iso") -> str:
    """
    Format datetime to string
    
    Args:
        dt: Datetime object
        format: Output format ('iso', 'human', 'date', 'time')
        
    Returns:
        Formatted timestamp string
    """
    if format == "iso":
        return dt.isoformat()
    elif format == "human":
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    elif format == "date":
        return dt.strftime("%Y-%m-%d")
    elif format == "time":
        return dt.strftime("%H:%M:%S")
    else:
        return dt.isoformat()


def parse_json_safely(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string
    
    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON or default value
    """
    if not json_str:
        return default
    
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Calculate file hash
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm ('md5', 'sha1', 'sha256')
        
    Returns:
        Hexadecimal hash string
    """
    hash_func = getattr(hashlib, algorithm)()
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def validate_file_type(filename: str, allowed_types: list) -> bool:
    """
    Validate file type by extension
    
    Args:
        filename: Filename to validate
        allowed_types: List of allowed extensions (e.g., ['.jpg', '.png'])
        
    Returns:
        True if valid, False otherwise
    """
    if not filename:
        return False
    
    extension = Path(filename).suffix.lower()
    return extension in [ext.lower() for ext in allowed_types]


def generate_unique_filename(original_filename: str, prefix: str = "") -> str:
    """
    Generate unique filename with UUID
    
    Args:
        original_filename: Original filename
        prefix: Optional prefix
        
    Returns:
        Unique filename
    """
    extension = Path(original_filename).suffix
    unique_id = uuid4().hex[:12]
    
    if prefix:
        return f"{prefix}_{unique_id}{extension}"
    else:
        return f"{unique_id}{extension}"


def extract_keywords(text: str, max_keywords: int = 10) -> list:
    """
    Extract keywords from text (simple implementation)
    
    Args:
        text: Input text
        max_keywords: Maximum number of keywords
        
    Returns:
        List of keywords
    """
    # Remove special characters and convert to lowercase
    words = re.findall(r'\b[a-zA-Z\u4e00-\u9fa5]{2,}\b', text.lower())
    
    # Count word frequency
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top N
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:max_keywords]]


def merge_dicts(dict1: Dict, dict2: Dict, deep: bool = True) -> Dict:
    """
    Merge two dictionaries
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
        deep: Whether to deep merge nested dicts
        
    Returns:
        Merged dictionary
    """
    if not deep:
        return {**dict1, **dict2}
    
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value, deep=True)
        else:
            result[key] = value
    
    return result


def chunk_list(lst: list, chunk_size: int) -> list:
    """
    Split list into chunks
    
    Args:
        lst: List to split
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def filter_none_values(d: Dict) -> Dict:
    """
    Remove None values from dictionary

    Args:
        d: Dictionary to filter

    Returns:
        Filtered dictionary
    """
    return {k: v for k, v in d.items() if v is not None}


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string (e.g., "1.5 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.1f} GB"


def parse_duration(duration_str: str) -> int:
    """
    Parse duration string to seconds

    Args:
        duration_str: Duration string (e.g., "1h30m", "45s", "2m30s")

    Returns:
        Duration in seconds
    """
    total_seconds = 0

    # Extract hours
    hours_match = re.search(r'(\d+)h', duration_str)
    if hours_match:
        total_seconds += int(hours_match.group(1)) * 3600

    # Extract minutes
    minutes_match = re.search(r'(\d+)m', duration_str)
    if minutes_match:
        total_seconds += int(minutes_match.group(1)) * 60

    # Extract seconds
    seconds_match = re.search(r'(\d+)s', duration_str)
    if seconds_match:
        total_seconds += int(seconds_match.group(1))

    return total_seconds


def is_valid_url(url: str) -> bool:
    """
    Check if string is a valid URL

    Args:
        url: URL string to validate

    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def extract_domain(url: str) -> str:
    """
    Extract base domain from URL (removes subdomains)

    Args:
        url: Full URL

    Returns:
        Base domain name (e.g., "example.com")
    """
    parsed = urlparse(url)
    domain = parsed.netloc

    # Remove 'www.' prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]

    # Extract base domain (last two parts: domain.tld)
    # This is a simple implementation - production would use public suffix list
    parts = domain.split('.')
    if len(parts) >= 2:
        domain = '.'.join(parts[-2:])

    return domain


def generate_slug(text: str) -> str:
    """
    Generate URL-friendly slug from text

    Args:
        text: Input text

    Returns:
        Slug string (lowercase, hyphen-separated)
    """
    # Convert to lowercase
    slug = text.lower()

    # Remove special characters
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)

    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)

    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)

    # Strip leading/trailing hyphens
    slug = slug.strip('-')

    return slug


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, handling division by zero

    Args:
        numerator: Number to divide
        denominator: Number to divide by
        default: Default value if division by zero

    Returns:
        Result of division or default value
    """
    if denominator == 0:
        return default
    return numerator / denominator


def dict_get_nested(data: Dict, path: str, default: Any = None) -> Any:
    """
    Get value from nested dictionary using dot notation

    Args:
        data: Dictionary to search
        path: Dot-separated path (e.g., "a.b.c")
        default: Default value if path not found

    Returns:
        Value at path or default
    """
    keys = path.split('.')
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current
