"""
Converter Utility Functions
数据格式转换工具函数
"""

import base64
import json
import re
from datetime import datetime
from typing import Any, Dict, Optional


def json_to_dict(json_str: str, default: Optional[Dict] = None) -> Dict:
    """
    Convert JSON string to dictionary
    
    Args:
        json_str: JSON string
        default: Default value if conversion fails
        
    Returns:
        Dictionary or default value
    """
    if not json_str:
        return default or {}
    
    try:
        result = json.loads(json_str)
        return result if isinstance(result, dict) else default or {}
    except (json.JSONDecodeError, TypeError):
        return default or {}


def dict_to_json(data: Dict, pretty: bool = False) -> str:
    """
    Convert dictionary to JSON string
    
    Args:
        data: Dictionary to convert
        pretty: Whether to format with indentation
        
    Returns:
        JSON string
    """
    if not data:
        return "{}"
    
    try:
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        return "{}"


def bytes_to_base64(data: bytes) -> str:
    """
    Convert bytes to base64 string
    
    Args:
        data: Bytes to convert
        
    Returns:
        Base64 encoded string
    """
    if not data:
        return ""
    
    return base64.b64encode(data).decode('utf-8')


def base64_to_bytes(base64_str: str) -> bytes:
    """
    Convert base64 string to bytes
    
    Args:
        base64_str: Base64 encoded string
        
    Returns:
        Decoded bytes
    """
    if not base64_str:
        return b""
    
    try:
        return base64.b64decode(base64_str)
    except Exception:
        return b""


def list_to_csv_string(items: list, delimiter: str = ",") -> str:
    """
    Convert list to CSV string
    
    Args:
        items: List of items
        delimiter: Delimiter character
        
    Returns:
        CSV string
    """
    if not items:
        return ""
    
    return delimiter.join(str(item) for item in items)


def csv_string_to_list(csv_str: str, delimiter: str = ",") -> list:
    """
    Convert CSV string to list
    
    Args:
        csv_str: CSV string
        delimiter: Delimiter character
        
    Returns:
        List of items
    """
    if not csv_str:
        return []
    
    return [item.strip() for item in csv_str.split(delimiter) if item.strip()]


def dict_to_query_string(params: Dict) -> str:
    """
    Convert dictionary to URL query string
    
    Args:
        params: Dictionary of parameters
        
    Returns:
        Query string (without leading '?')
    """
    if not params:
        return ""
    
    parts = []
    for key, value in params.items():
        if value is not None:
            parts.append(f"{key}={value}")
    
    return "&".join(parts)


def bytes_to_human_readable(size_bytes: int) -> str:
    """
    Convert bytes to human-readable size

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable string (e.g., "1.5 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.1f} GB"


def seconds_to_human_readable(seconds: int) -> str:
    """
    Convert seconds to human-readable duration

    Args:
        seconds: Duration in seconds

    Returns:
        Human-readable string (e.g., "2h 30m")
    """
    if seconds < 0:
        return "0s"

    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}h {remaining_minutes}m"


def flatten_dict(nested_dict: Dict, parent_key: str = '', separator: str = '.') -> Dict:
    """
    Flatten nested dictionary

    Args:
        nested_dict: Nested dictionary
        parent_key: Parent key prefix
        separator: Key separator

    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in nested_dict.items():
        new_key = f"{parent_key}{separator}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, separator=separator).items())
        else:
            items.append((new_key, v))
    return dict(items)


def timestamp_to_iso(dt: datetime) -> str:
    """
    Convert datetime to ISO format string

    Args:
        dt: Datetime object

    Returns:
        ISO format string
    """
    return dt.isoformat()


def iso_to_timestamp(iso_string: str) -> datetime:
    """
    Convert ISO format string to datetime

    Args:
        iso_string: ISO format string

    Returns:
        Datetime object
    """
    return datetime.fromisoformat(iso_string.replace('Z', '+00:00'))


def query_string_to_dict(query_string: str) -> Dict[str, str]:
    """
    Convert URL query string to dictionary

    Args:
        query_string: Query string (without leading '?')

    Returns:
        Dictionary of parameters
    """
    if not query_string:
        return {}

    params = {}
    for part in query_string.split('&'):
        if '=' in part:
            key, value = part.split('=', 1)
            params[key] = value

    return params


def snake_to_camel(snake_str: str) -> str:
    """
    Convert snake_case to camelCase

    Args:
        snake_str: Snake case string

    Returns:
        Camel case string
    """
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def camel_to_snake(camel_str: str) -> str:
    """
    Convert camelCase to snake_case

    Args:
        camel_str: Camel case string

    Returns:
        Snake case string
    """
    snake = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', snake).lower()


def list_to_comma_separated(items: list) -> str:
    """
    Convert list to comma-separated string

    Args:
        items: List of items

    Returns:
        Comma-separated string
    """
    if not items:
        return ""

    return ", ".join(str(item) for item in items)


def comma_separated_to_list(text: str) -> list:
    """
    Convert comma-separated string to list

    Args:
        text: Comma-separated string

    Returns:
        List of items
    """
    if not text:
        return []

    return [item.strip() for item in text.split(',') if item.strip()]
