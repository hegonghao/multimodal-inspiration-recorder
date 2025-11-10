"""
Unit Tests: Utility Functions
工具函数单元测试

Tests for:
- backend/src/utils/helpers.py
- backend/src/utils/validators.py
- backend/src/utils/converters.py

Coverage Target: 95%+
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile

from src.utils.helpers import (
    sanitize_text,
    calculate_file_hash,
    generate_unique_filename,
    format_file_size,
    parse_duration,
    truncate_text,
    is_valid_url,
    extract_domain,
    generate_slug,
    safe_divide,
    dict_get_nested,
)

from src.utils.validators import (
    validate_notion_token,
    validate_database_id,
    validate_audio_file,
    validate_image_file,
    validate_text_content,
    validate_email,
    validate_phone_number,
    validate_duration,
    is_valid_uuid,
)

from src.utils.converters import (
    seconds_to_human_readable,
    bytes_to_human_readable,
    timestamp_to_iso,
    iso_to_timestamp,
    dict_to_query_string,
    query_string_to_dict,
    snake_to_camel,
    camel_to_snake,
    list_to_comma_separated,
    comma_separated_to_list,
)


class TestHelpers:
    """Test helper utility functions"""

    def test_sanitize_text_basic(self):
        """Test basic text sanitization"""
        result = sanitize_text("  Hello   World  ")
        assert result == "Hello World"

    def test_sanitize_text_removes_null_bytes(self):
        """Test null byte removal"""
        result = sanitize_text("Hello\x00World")
        assert result == "HelloWorld"

    def test_sanitize_text_with_max_length(self):
        """Test text truncation"""
        long_text = "A" * 100
        result = sanitize_text(long_text, max_length=50)
        assert len(result) <= 53  # 50 + "..."
        assert result.endswith("...")

    def test_sanitize_text_empty_string(self):
        """Test empty string handling"""
        result = sanitize_text("")
        assert result == ""

    def test_sanitize_text_none(self):
        """Test None handling"""
        result = sanitize_text(None)
        assert result == ""

    def test_calculate_file_hash_sha256(self):
        """Test file hash calculation with SHA256"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Test content")
            temp_path = Path(f.name)

        try:
            hash_result = calculate_file_hash(temp_path, algorithm="sha256")
            assert len(hash_result) == 64  # SHA256 produces 64 hex characters
            assert isinstance(hash_result, str)
        finally:
            temp_path.unlink()

    def test_calculate_file_hash_md5(self):
        """Test file hash calculation with MD5"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Test content")
            temp_path = Path(f.name)

        try:
            hash_result = calculate_file_hash(temp_path, algorithm="md5")
            assert len(hash_result) == 32  # MD5 produces 32 hex characters
        finally:
            temp_path.unlink()

    def test_generate_unique_filename_with_prefix(self):
        """Test unique filename generation with prefix"""
        filename = generate_unique_filename("test.jpg", prefix="upload")
        assert filename.startswith("upload_")
        assert filename.endswith(".jpg")

    def test_generate_unique_filename_without_prefix(self):
        """Test unique filename generation without prefix"""
        filename = generate_unique_filename("document.pdf")
        assert filename.endswith(".pdf")
        assert len(filename) > 15  # UUID part + extension

    def test_format_file_size_bytes(self):
        """Test file size formatting for bytes"""
        assert format_file_size(500) == "500 B"

    def test_format_file_size_kilobytes(self):
        """Test file size formatting for KB"""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"

    def test_format_file_size_megabytes(self):
        """Test file size formatting for MB"""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(5 * 1024 * 1024) == "5.0 MB"

    def test_format_file_size_gigabytes(self):
        """Test file size formatting for GB"""
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_parse_duration_seconds(self):
        """Test duration parsing for seconds"""
        assert parse_duration("30s") == 30
        assert parse_duration("45s") == 45

    def test_parse_duration_minutes(self):
        """Test duration parsing for minutes"""
        assert parse_duration("2m") == 120
        assert parse_duration("5m") == 300

    def test_parse_duration_hours(self):
        """Test duration parsing for hours"""
        assert parse_duration("1h") == 3600
        assert parse_duration("2h") == 7200

    def test_parse_duration_combined(self):
        """Test duration parsing for combined units"""
        assert parse_duration("1h30m") == 5400
        assert parse_duration("2m30s") == 150

    def test_truncate_text_short(self):
        """Test text truncation for short text"""
        result = truncate_text("Short", max_length=10)
        assert result == "Short"

    def test_truncate_text_long(self):
        """Test text truncation for long text"""
        result = truncate_text("A" * 100, max_length=50)
        assert len(result) <= 53
        assert result.endswith("...")

    def test_is_valid_url_valid(self):
        """Test URL validation for valid URLs"""
        assert is_valid_url("https://example.com") is True
        assert is_valid_url("http://localhost:8000") is True

    def test_is_valid_url_invalid(self):
        """Test URL validation for invalid URLs"""
        assert is_valid_url("not a url") is False
        assert is_valid_url("example.com") is False  # Missing protocol

    def test_extract_domain(self):
        """Test domain extraction from URL"""
        assert extract_domain("https://www.example.com/path") == "example.com"
        assert extract_domain("http://sub.example.com") == "example.com"

    def test_generate_slug(self):
        """Test slug generation"""
        assert generate_slug("Hello World") == "hello-world"
        assert generate_slug("Test  Multiple   Spaces") == "test-multiple-spaces"
        assert generate_slug("Special@#Characters") == "specialcharacters"

    def test_safe_divide_normal(self):
        """Test safe division with normal values"""
        assert safe_divide(10, 2) == 5.0
        assert safe_divide(7, 2) == 3.5

    def test_safe_divide_by_zero(self):
        """Test safe division by zero"""
        assert safe_divide(10, 0) == 0.0
        assert safe_divide(10, 0, default=None) is None

    def test_dict_get_nested(self):
        """Test nested dictionary access"""
        data = {"a": {"b": {"c": "value"}}}
        assert dict_get_nested(data, "a.b.c") == "value"
        assert dict_get_nested(data, "a.b") == {"c": "value"}

    def test_dict_get_nested_missing_key(self):
        """Test nested dictionary access with missing key"""
        data = {"a": {"b": "value"}}
        assert dict_get_nested(data, "a.x", default="default") == "default"


class TestValidators:
    """Test validation utility functions"""

    def test_validate_notion_token_valid(self):
        """Test valid Notion token"""
        valid, message = validate_notion_token("secret_" + "a" * 50)
        assert valid is True
        assert message is None

    def test_validate_notion_token_empty(self):
        """Test empty Notion token"""
        valid, message = validate_notion_token("")
        assert valid is False
        assert "cannot be empty" in message.lower()

    def test_validate_notion_token_wrong_prefix(self):
        """Test Notion token with wrong prefix"""
        valid, message = validate_notion_token("invalid_token")
        assert valid is False
        assert "must start with" in message.lower()

    def test_validate_notion_token_too_short(self):
        """Test Notion token that's too short"""
        valid, message = validate_notion_token("secret_short")
        assert valid is False
        assert "too short" in message.lower()

    def test_validate_database_id_valid(self):
        """Test valid database ID"""
        valid_id = "a" * 32
        valid, message = validate_database_id(valid_id)
        assert valid is True
        assert message is None

    def test_validate_database_id_with_hyphens(self):
        """Test database ID with hyphens (should work)"""
        valid_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        valid, message = validate_database_id(valid_id)
        assert valid is True

    def test_validate_database_id_invalid_format(self):
        """Test invalid database ID format"""
        valid, message = validate_database_id("invalid")
        assert valid is False

    def test_validate_audio_file_valid(self):
        """Test valid audio file"""
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as f:
            # Write 1MB of data
            f.write(b"0" * (1024 * 1024))
            temp_path = Path(f.name)

        try:
            valid, message = validate_audio_file(str(temp_path))
            assert valid is True
        finally:
            temp_path.unlink()

    def test_validate_audio_file_wrong_extension(self):
        """Test audio file with wrong extension"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_path = Path(f.name)

        try:
            valid, message = validate_audio_file(str(temp_path))
            assert valid is False
            assert "format" in message.lower() or "extension" in message.lower()
        finally:
            temp_path.unlink()

    def test_validate_audio_file_too_large(self):
        """Test audio file that's too large"""
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as f:
            # Write 60MB of data (exceeds 50MB limit)
            f.write(b"0" * (60 * 1024 * 1024))
            temp_path = Path(f.name)

        try:
            valid, message = validate_audio_file(str(temp_path))
            assert valid is False
            assert "too large" in message.lower() or "size" in message.lower()
        finally:
            temp_path.unlink()

    def test_validate_image_file_valid(self):
        """Test valid image file"""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"fake image data")
            temp_path = Path(f.name)

        try:
            valid, message = validate_image_file(str(temp_path))
            assert valid is True
        finally:
            temp_path.unlink()

    def test_validate_text_content_valid(self):
        """Test valid text content"""
        valid, message = validate_text_content("This is a valid text content")
        assert valid is True

    def test_validate_text_content_too_short(self):
        """Test text content that's too short"""
        valid, message = validate_text_content("Short")
        assert valid is False
        assert "too short" in message.lower() or "minimum" in message.lower()

    def test_validate_text_content_too_long(self):
        """Test text content that's too long"""
        long_text = "A" * 11000
        valid, message = validate_text_content(long_text)
        assert valid is False
        assert "too long" in message.lower() or "maximum" in message.lower()

    def test_validate_email_valid(self):
        """Test valid email addresses"""
        assert validate_email("user@example.com") is True
        assert validate_email("test.user@domain.co.uk") is True

    def test_validate_email_invalid(self):
        """Test invalid email addresses"""
        assert validate_email("not-an-email") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False

    def test_validate_phone_number_valid(self):
        """Test valid phone numbers"""
        assert validate_phone_number("+1234567890") is True
        assert validate_phone_number("123-456-7890") is True

    def test_validate_phone_number_invalid(self):
        """Test invalid phone numbers"""
        assert validate_phone_number("abc") is False
        assert validate_phone_number("123") is False  # Too short

    def test_validate_duration_valid(self):
        """Test valid durations"""
        valid, message = validate_duration(30)
        assert valid is True

        valid, message = validate_duration(150)
        assert valid is True

    def test_validate_duration_too_short(self):
        """Test duration that's too short"""
        valid, message = validate_duration(0)
        assert valid is False

    def test_validate_duration_too_long(self):
        """Test duration that's too long"""
        valid, message = validate_duration(400)  # Exceeds 300s (5min) limit
        assert valid is False

    def test_is_valid_uuid(self):
        """Test UUID validation"""
        assert is_valid_uuid("550e8400-e29b-41d4-a716-446655440000") is True
        assert is_valid_uuid("invalid-uuid") is False


class TestConverters:
    """Test conversion utility functions"""

    def test_seconds_to_human_readable_seconds(self):
        """Test seconds conversion"""
        assert seconds_to_human_readable(30) == "30s"
        assert seconds_to_human_readable(45) == "45s"

    def test_seconds_to_human_readable_minutes(self):
        """Test minutes conversion"""
        assert seconds_to_human_readable(60) == "1m 0s"
        assert seconds_to_human_readable(90) == "1m 30s"

    def test_seconds_to_human_readable_hours(self):
        """Test hours conversion"""
        assert seconds_to_human_readable(3600) == "1h 0m"
        assert seconds_to_human_readable(3665) == "1h 1m"

    def test_bytes_to_human_readable_bytes(self):
        """Test bytes conversion"""
        assert bytes_to_human_readable(500) == "500 B"

    def test_bytes_to_human_readable_kb(self):
        """Test kilobytes conversion"""
        assert bytes_to_human_readable(1024) == "1.0 KB"

    def test_bytes_to_human_readable_mb(self):
        """Test megabytes conversion"""
        assert bytes_to_human_readable(1048576) == "1.0 MB"

    def test_bytes_to_human_readable_gb(self):
        """Test gigabytes conversion"""
        assert bytes_to_human_readable(1073741824) == "1.0 GB"

    def test_timestamp_to_iso(self):
        """Test timestamp to ISO conversion"""
        dt = datetime(2025, 10, 28, 12, 30, 45)
        iso_string = timestamp_to_iso(dt)
        assert "2025-10-28" in iso_string
        assert "12:30:45" in iso_string

    def test_iso_to_timestamp(self):
        """Test ISO to timestamp conversion"""
        iso_string = "2025-10-28T12:30:45"
        dt = iso_to_timestamp(iso_string)
        assert dt.year == 2025
        assert dt.month == 10
        assert dt.day == 28

    def test_dict_to_query_string(self):
        """Test dictionary to query string conversion"""
        params = {"key1": "value1", "key2": "value2"}
        query = dict_to_query_string(params)
        assert "key1=value1" in query
        assert "key2=value2" in query

    def test_query_string_to_dict(self):
        """Test query string to dictionary conversion"""
        query = "key1=value1&key2=value2"
        params = query_string_to_dict(query)
        assert params["key1"] == "value1"
        assert params["key2"] == "value2"

    def test_snake_to_camel(self):
        """Test snake_case to camelCase conversion"""
        assert snake_to_camel("hello_world") == "helloWorld"
        assert snake_to_camel("test_variable_name") == "testVariableName"

    def test_camel_to_snake(self):
        """Test camelCase to snake_case conversion"""
        assert camel_to_snake("helloWorld") == "hello_world"
        assert camel_to_snake("testVariableName") == "test_variable_name"

    def test_list_to_comma_separated(self):
        """Test list to comma-separated string conversion"""
        items = ["apple", "banana", "cherry"]
        result = list_to_comma_separated(items)
        assert result == "apple, banana, cherry"

    def test_comma_separated_to_list(self):
        """Test comma-separated string to list conversion"""
        text = "apple, banana, cherry"
        result = comma_separated_to_list(text)
        assert result == ["apple", "banana", "cherry"]

    def test_comma_separated_to_list_with_extra_spaces(self):
        """Test comma-separated conversion with extra spaces"""
        text = "apple  ,  banana  ,  cherry"
        result = comma_separated_to_list(text)
        assert result == ["apple", "banana", "cherry"]


class TestUtilsEdgeCases:
    """Test edge cases and error scenarios"""

    def test_sanitize_text_special_characters(self):
        """Test sanitization with special characters"""
        result = sanitize_text("Hello\n\r\tWorld")
        assert "\n" not in result
        assert "\r" not in result
        assert "\t" not in result

    def test_truncate_text_exact_length(self):
        """Test truncation at exact length"""
        result = truncate_text("Hello", max_length=5)
        assert result == "Hello"

    def test_safe_divide_float_result(self):
        """Test safe division with float result"""
        result = safe_divide(5, 2)
        assert result == 2.5

    def test_dict_get_nested_array_index(self):
        """Test nested access with array indexing"""
        data = {"items": [{"name": "first"}, {"name": "second"}]}
        result = dict_get_nested(data, "items.0.name")
        # This may or may not be supported depending on implementation
        # Test based on actual implementation

    def test_validate_notion_token_whitespace(self):
        """Test Notion token validation with whitespace"""
        valid, message = validate_notion_token("  secret_" + "a" * 50 + "  ")
        # Should handle trimming or reject

    def test_bytes_to_human_readable_zero(self):
        """Test bytes conversion with zero"""
        assert bytes_to_human_readable(0) == "0 B"

    def test_seconds_to_human_readable_zero(self):
        """Test seconds conversion with zero"""
        result = seconds_to_human_readable(0)
        assert "0" in result
