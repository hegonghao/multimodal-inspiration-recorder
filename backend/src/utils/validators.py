"""
Validation Utility Functions
数据验证工具函数
"""

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from uuid import UUID


def validate_url(url: str) -> bool:
    """
    Validate URL format
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    if not url:
        return False
    
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email string to validate
        
    Returns:
        True if valid email, False otherwise
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_notion_token(token: str) -> tuple[bool, Optional[str]]:
    """
    Validate Notion API token format
    
    Args:
        token: Notion token to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not token:
        return False, "Token cannot be empty"
    
    # Notion tokens typically start with 'secret_'
    if not token.startswith('secret_'):
        return False, "Invalid token format: must start with 'secret_'"
    
    # Check minimum length
    if len(token) < 50:
        return False, "Token too short"
    
    return True, None


def validate_database_id(database_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate Notion database ID format
    
    Args:
        database_id: Database ID to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not database_id:
        return False, "Database ID cannot be empty"
    
    # Remove hyphens for validation
    clean_id = database_id.replace('-', '')
    
    # Check if it's a valid hex string
    if not re.match(r'^[0-9a-f]{32}$', clean_id, re.IGNORECASE):
        return False, "Invalid database ID format (must be 32-character hex string)"
    
    return True, None


def validate_content_length(content: str, min_length: int = 10, max_length: int = 10000) -> tuple[bool, Optional[str]]:
    """
    Validate content length
    
    Args:
        content: Content to validate
        min_length: Minimum length
        max_length: Maximum length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not content:
        return False, "Content cannot be empty"
    
    content_len = len(content.strip())
    
    if content_len < min_length:
        return False, f"Content too short (minimum {min_length} characters)"
    
    if content_len > max_length:
        return False, f"Content too long (maximum {max_length} characters)"
    
    return True, None


def validate_api_key(api_key: str, min_length: int = 20) -> tuple[bool, Optional[str]]:
    """
    Validate API key format
    
    Args:
        api_key: API key to validate
        min_length: Minimum key length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not api_key:
        return False, "API key cannot be empty"
    
    if len(api_key) < min_length:
        return False, f"API key too short (minimum {min_length} characters)"
    
    # Check for common invalid patterns
    if api_key.lower() in ['test', 'example', 'demo', 'placeholder']:
        return False, "Invalid API key (placeholder value)"
    
    return True, None


def validate_language_code(lang_code: str) -> bool:
    """
    Validate language code (ISO 639-1)
    
    Args:
        lang_code: Language code to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not lang_code:
        return False
    
    # Common language codes
    valid_codes = ['zh', 'en', 'zh-CN', 'zh-TW', 'en-US', 'en-GB', 'ja', 'ko', 'fr', 'de', 'es']
    return lang_code in valid_codes


def validate_file_size(file_size: int, max_size: int = 50 * 1024 * 1024) -> tuple[bool, Optional[str]]:
    """
    Validate file size
    
    Args:
        file_size: File size in bytes
        max_size: Maximum allowed size in bytes (default 50MB)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if file_size <= 0:
        return False, "Invalid file size"
    
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"File too large (maximum {max_mb:.1f}MB)"
    
    return True, None


def validate_json_structure(data: dict, required_fields: list) -> tuple[bool, Optional[str]]:
    """
    Validate JSON structure has required fields

    Args:
        data: Dictionary to validate
        required_fields: List of required field names

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Data must be a dictionary"

    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"

    return True, None


def validate_audio_file(file_path: str, max_size: int = 50 * 1024 * 1024) -> tuple[bool, Optional[str]]:
    """
    Validate audio file

    Args:
        file_path: Path to audio file
        max_size: Maximum file size in bytes (default 50MB)

    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(file_path)

    if not path.exists():
        return False, "File does not exist"

    # Check extension
    allowed_extensions = [".m4a", ".mp3", ".wav", ".webm", ".ogg"]
    if path.suffix.lower() not in allowed_extensions:
        return False, f"Invalid audio format. Allowed: {', '.join(allowed_extensions)}"

    # Check file size
    file_size = path.stat().st_size
    if file_size > max_size:
        return False, f"File too large. Maximum size: {max_size / (1024 * 1024):.0f}MB"

    return True, None


def validate_image_file(file_path: str, max_size: int = 50 * 1024 * 1024) -> tuple[bool, Optional[str]]:
    """
    Validate image file

    Args:
        file_path: Path to image file
        max_size: Maximum file size in bytes (default 50MB)

    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(file_path)

    if not path.exists():
        return False, "File does not exist"

    # Check extension
    allowed_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
    if path.suffix.lower() not in allowed_extensions:
        return False, f"Invalid image format. Allowed: {', '.join(allowed_extensions)}"

    # Check file size
    file_size = path.stat().st_size
    if file_size > max_size:
        return False, f"File too large. Maximum size: {max_size / (1024 * 1024):.0f}MB"

    return True, None


def validate_text_content(text: str, min_length: int = 10, max_length: int = 10000) -> tuple[bool, Optional[str]]:
    """
    Validate text content

    Args:
        text: Text content to validate
        min_length: Minimum text length
        max_length: Maximum text length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text:
        return False, "Text cannot be empty"

    if len(text) < min_length:
        return False, f"Text too short. Minimum length: {min_length} characters"

    if len(text) > max_length:
        return False, f"Text too long. Maximum length: {max_length} characters"

    return True, None


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number

    Args:
        phone: Phone number to validate

    Returns:
        True if valid, False otherwise
    """
    if not phone:
        return False

    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)

    # Check if it's a valid phone number (10-15 digits, optional + prefix)
    pattern = r'^\+?\d{10,15}$'
    return bool(re.match(pattern, cleaned))


def validate_duration(duration_seconds: int, min_duration: int = 1, max_duration: int = 300) -> tuple[bool, Optional[str]]:
    """
    Validate duration in seconds

    Args:
        duration_seconds: Duration to validate
        min_duration: Minimum duration (default 1 second)
        max_duration: Maximum duration (default 300 seconds / 5 minutes)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if duration_seconds < min_duration:
        return False, f"Duration too short. Minimum: {min_duration}s"

    if duration_seconds > max_duration:
        return False, f"Duration too long. Maximum: {max_duration}s"

    return True, None


def is_valid_uuid(uuid_string: str) -> bool:
    """
    Validate UUID string

    Args:
        uuid_string: UUID string to validate

    Returns:
        True if valid UUID, False otherwise
    """
    try:
        UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False
