"""
Performance Tests Package

Constitution Principle II - Performance Requirements Validation

This package contains performance tests for:
- T088: Voice recording start time (<5s requirement)
- T090: OCR processing time (<5s requirement)

Performance Targets:
- UI Response Time: <1s (validated in Flutter tests)
- Recording Start: <5s
- OCR Processing: <5s
- AI Classification: <3s
- Notion Sync: <30s

Usage:
    pytest backend/tests/performance/ -v -m performance
"""
