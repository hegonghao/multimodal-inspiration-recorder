"""
Records API Endpoints

Handles CRUD operations for inspiration records with multimodal input support
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional
from datetime import datetime
import tempfile
import os

from src.database.connection import get_db
from src.models.inspiration import (
    InspirationRecord,
    InspirationRecordCreate,
    InspirationRecordUpdate,
    InspirationRecordResponse,
    InspirationRecordListResponse,
    serialize_category_tags,
)
from src.models.sync_queue import SyncQueue, SyncOperation
from src.models.user_preferences import UserPreferences
from src.services.speech_to_text import get_speech_service
from src.services.ocr_service import get_ocr_service
from src.services.ai_processor import get_ai_processor
from src.utils.logger import get_logger
from src.core.exceptions import ExternalServiceException

router = APIRouter()
logger = get_logger(__name__)

# Quality thresholds for content validation
MIN_TRANSCRIPTION_CONFIDENCE = 0.05  # Minimum confidence for voice transcription (5% - very low to support mixed Chinese-English)
MIN_OCR_CONFIDENCE = 0.4  # Minimum confidence for OCR (40% - lower due to image quality variance)
MIN_CONTENT_LENGTH = 10  # Minimum characters for extracted content

# Language-specific warning thresholds for transcription
# English tends to have lower word-level confidence scores than Chinese
WARN_TRANSCRIPTION_CONFIDENCE_ZH = 0.40  # 40% for Chinese
WARN_TRANSCRIPTION_CONFIDENCE_EN = 0.25  # 25% for English (lower due to Deepgram scoring characteristics)
WARN_TRANSCRIPTION_CONFIDENCE_DEFAULT = 0.30  # 30% for other languages

WARN_OCR_CONFIDENCE = 0.6  # Warning threshold for OCR


@router.get("", response_model=InspirationRecordListResponse)
async def list_records(
    page: int = 1,
    page_size: int = 20,
    input_type: Optional[str] = None,
    sync_status: Optional[int] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated list of inspiration records with optional filtering

    Query parameters:
    - page: Page number (1-indexed)
    - page_size: Number of records per page (max 100)
    - input_type: Filter by input type ('text', 'voice', 'image')
    - sync_status: Filter by sync status (0=not synced, 1=synced, 2=failed)
    - search: Search in title and content
    - sort_by: Sort field ('created_at', 'updated_at', 'title')
    - sort_order: Sort order ('asc', 'desc')
    """
    # Validate pagination
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be >= 1"
        )
    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be between 1 and 100"
        )

    # Build query with filters
    query = select(InspirationRecord)

    # Filter by input_type
    if input_type:
        query = query.where(InspirationRecord.input_type == input_type)

    # Filter by sync_status
    if sync_status is not None:
        query = query.where(InspirationRecord.sync_status == sync_status)

    # Search in title and content
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                InspirationRecord.title.like(search_pattern),
                InspirationRecord.content.like(search_pattern)
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_count = total_result.scalar()

    # Apply sorting
    sort_column = getattr(InspirationRecord, sort_by, InspirationRecord.created_at)
    if sort_order.lower() == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    records = result.scalars().all()

    # Calculate pagination metadata
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    return {
        "data": records,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


@router.post("", response_model=InspirationRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_text_record(
    record: InspirationRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new text-based inspiration record (JSON API)

    Simple JSON endpoint for text-only records without file upload.
    For voice/image records with files, use POST /api/v1/records/upload instead.

    Request body (JSON):
    {
        "title": "Record title",
        "content": "Text content",
        "input_type": "text"
    }

    Returns:
        Created inspiration record
    """
    try:
        logger.info(f"Creating text record via JSON API: {record.input_type}")

        # Validate this endpoint is only for text input
        if record.input_type != "text":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This endpoint only accepts input_type='text'. For {record.input_type} input, use POST /api/v1/records/upload"
            )

        # Validate content
        if not record.content or len(record.content.strip()) < MIN_CONTENT_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Content must be at least {MIN_CONTENT_LENGTH} characters"
            )

        # Generate title from content if not provided
        title = record.title or (record.content[:50] + ("..." if len(record.content) > 50 else ""))

        # Create database record (no AI processing for now)
        new_record = InspirationRecord(
            title=title,
            content=record.content,
            input_type="text",
            sync_status=0,  # Not synced
            ai_processing_status=0,  # Pending
            version=1,
        )

        db.add(new_record)
        await db.flush()

        # Create sync queue entry
        sync_task = SyncQueue(
            record_id=new_record.id,
            operation=SyncOperation.CREATE,
            status=0,  # PENDING
            retry_count=0,
            max_retries=5,
            priority=0,  # NORMAL
        )

        db.add(sync_task)
        await db.commit()
        await db.refresh(new_record)

        logger.info(f"Text record created: id={new_record.id}")

        return new_record

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create text record: {type(e).__name__}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create record: {str(e)}"
        )


@router.post("/upload", response_model=InspirationRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_record_with_file(
    input_type: str = Form(...),
    content: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    language: Optional[str] = Form("zh"),
    auto_process: bool = Form(True),
    use_chart_recognition: bool = Form(False),
    use_orientation_classify: bool = Form(False),
    use_unwarping: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new inspiration record with file upload (voice/image/pdf)

    Supports file-based input types:
    - voice: Upload audio file for transcription
    - image: Upload image for OCR (with optional chart recognition and correction)
    - pdf: Upload PDF document for multi-page OCR

    Args:
        input_type: Type of input ('voice', 'image', 'pdf')
        content: Optional text content
        file: Audio/image/PDF file (required)
        language: Content language ('zh', 'en')
        auto_process: Whether to automatically process with AI (categorize, summarize)
        use_chart_recognition: Enable chart/table recognition (OCR only)
        use_orientation_classify: Enable document orientation correction (OCR only)
        use_unwarping: Enable document unwarping for skewed images (OCR only)
        db: Database session

    Returns:
        Created inspiration record
    """
    try:
        logger.info(f"Creating record: input_type={input_type}, auto_process={auto_process}")

        # Validate input based on type
        if input_type not in ["voice", "image", "pdf", "text"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid input_type: {input_type}. Must be 'voice', 'image', 'pdf', or 'text'"
            )

        # Process content based on input type
        extracted_content = ""
        content_markdown = None  # Markdown content (for OCR/PDF)
        processing_metadata = {}
        file_path = None  # File path for storage
        page_count = None  # Number of pages (for PDF)

        if input_type == "text":
            # Direct text input
            if not content or len(content.strip()) < 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Text content must be at least 10 characters"
                )
            extracted_content = content
            processing_metadata = {
                "word_count": len(content.split()),
                "char_count": len(content)
            }

        elif input_type == "voice":
            # Voice input - require file
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Audio file is required for voice input"
                )

            # Save uploaded file temporarily
            file_content = await file.read()
            # Detect file extension from filename or default to .wav
            file_ext = ".wav"  # Default to WAV
            if file.filename:
                if file.filename.endswith(".wav"):
                    file_ext = ".wav"
                elif file.filename.endswith(".m4a"):
                    file_ext = ".m4a"
                elif file.filename.endswith(".aac"):
                    file_ext = ".aac"

            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                temp_file.write(file_content)
                temp_file.flush()  # CRITICAL: Flush to ensure data is written to disk
                temp_file_path = temp_file.name

            # Log file information for debugging
            file_size = len(file_content)
            logger.info(
                f"Audio file uploaded: size={file_size} bytes, "
                f"filename={file.filename}, content_type={file.content_type}"
            )

            if file_size == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded audio file is empty"
                )

            # Save a copy for debugging (only for first few uploads)
            import shutil
            debug_dir = "/app/uploads/audio"
            os.makedirs(debug_dir, exist_ok=True)
            debug_path = os.path.join(debug_dir, f"debug_{os.path.basename(temp_file_path)}")
            shutil.copy(temp_file_path, debug_path)
            logger.info(f"Saved debug copy to: {debug_path}")

            try:
                # Get user preferences for Deepgram API key
                prefs_result = await db.execute(
                    select(UserPreferences).where(UserPreferences.id == 1)
                )
                user_prefs = prefs_result.scalar_one_or_none()

                if not user_prefs or not user_prefs.deepgram_api_key:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail={
                            "error": "configuration_error",
                            "message": "Deepgram API key not configured. Please configure it in settings.",
                        }
                    )

                # Transcribe audio with user's API key
                speech_service = get_speech_service(api_key=user_prefs.deepgram_api_key)

                try:
                    # Use user's language preference
                    # If language is 'auto', enable auto-detection
                    # If language is specified (zh/en), use it directly
                    use_auto_detect = language == "auto"
                    language_param = None if use_auto_detect else language

                    logger.info(
                        f"Transcription settings: language='{language}', "
                        f"auto_detect={use_auto_detect}, language_param={language_param}"
                    )

                    transcription_result = await speech_service.transcribe_audio_file(
                        temp_file_path,
                        language=language_param,  # Use specified language or None for auto-detect
                        detect_language=use_auto_detect  # Enable detection only when language is 'auto'
                    )
                except Exception as trans_error:
                    logger.error(f"Transcription service failed: {trans_error}")
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "transcription_failed",
                            "message": "Failed to transcribe audio. Please ensure the audio is clear and contains speech.",
                            "details": str(trans_error)
                        }
                    )

                extracted_content = transcription_result["text"]
                confidence = transcription_result["confidence"]
                detected_language = transcription_result["language"]

                processing_metadata = {
                    "transcription_confidence": confidence,
                    "detected_language": detected_language,
                    "audio_duration": transcription_result["duration"],
                    "word_count": transcription_result["word_count"],
                }

                # Reject only if confidence is extremely low (< 5%)
                if confidence < MIN_TRANSCRIPTION_CONFIDENCE:
                    logger.error(
                        f"Extremely low transcription confidence: {confidence:.2%} < {MIN_TRANSCRIPTION_CONFIDENCE:.2%}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "transcription_failed",
                            "message": "无法识别音频内容,可能音频为空或损坏",
                            "confidence": confidence,
                            "threshold": MIN_TRANSCRIPTION_CONFIDENCE,
                            "suggestions": [
                                "检查录音是否包含语音",
                                "确保麦克风正常工作",
                                "尝试重新录制"
                            ]
                        }
                    )

                # Select language-specific warning threshold
                # English tends to have lower confidence scores than Chinese due to Deepgram's scoring model
                if detected_language and detected_language.startswith("zh"):
                    warn_threshold = WARN_TRANSCRIPTION_CONFIDENCE_ZH
                    lang_label = "中文"
                elif detected_language and detected_language.startswith("en"):
                    warn_threshold = WARN_TRANSCRIPTION_CONFIDENCE_EN
                    lang_label = "英文"
                else:
                    warn_threshold = WARN_TRANSCRIPTION_CONFIDENCE_DEFAULT
                    lang_label = detected_language or "未知语言"

                # Warn if confidence is below language-specific threshold
                if confidence < warn_threshold:
                    logger.warning(
                        f"Low transcription confidence: {confidence:.2%} < {warn_threshold:.2%} "
                        f"(detected language: {detected_language})"
                    )
                    processing_metadata["confidence_warning"] = True
                    processing_metadata["manual_review_recommended"] = True
                    processing_metadata["warning_message"] = (
                        f"识别置信度较低 ({confidence:.1%} < {warn_threshold:.1%}), "
                        f"检测到的语言: {lang_label}。建议检查并手动修正识别内容。"
                    )
                else:
                    logger.info(
                        f"Transcription confidence acceptable: {confidence:.2%} >= {warn_threshold:.2%} "
                        f"(detected language: {detected_language})"
                    )

                logger.info(
                    f"Transcription completed: {transcription_result['word_count']} words, "
                    f"confidence: {confidence:.2f}"
                )

            finally:
                # Clean up temp file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        elif input_type in ["image", "pdf"]:
            # Image/PDF input - require file
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{input_type.title()} file is required for {input_type} input"
                )

            # Determine file extension
            file_ext = ".jpg" if input_type == "image" else ".pdf"
            if file.filename:
                ext_from_name = os.path.splitext(file.filename)[1]
                if ext_from_name:
                    file_ext = ext_from_name

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                temp_file.write(await file.read())
                temp_file_path = temp_file.name

            try:
                # Perform OCR with PaddleOCR
                ocr_service = get_ocr_service()
                language_hints = [language] if language != "auto" else None

                try:
                    ocr_result = await ocr_service.extract_text_from_image(
                        temp_file_path,
                        language_hints=language_hints,
                        use_chart_recognition=use_chart_recognition,
                        use_orientation_classify=use_orientation_classify,
                        use_unwarping=use_unwarping,
                    )
                except Exception as ocr_error:
                    logger.error(f"OCR service failed: {ocr_error}")
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "ocr_failed",
                            "message": f"Failed to extract text from {input_type}. Please ensure the {input_type} contains clear, readable text.",
                            "details": str(ocr_error),
                            "fallback": "manual_input",
                            "suggestions": [
                                "Ensure the image is clear and well-lit",
                                "Check that text is not too small",
                                "Avoid blurry or low-resolution images",
                                "Try taking a new photo" if input_type == "image" else "Try a different PDF",
                                "Manually input the text instead"
                            ]
                        }
                    )

                extracted_content = ocr_result["text"]
                content_markdown = ocr_result.get("markdown", "")  # Get Markdown output
                confidence = ocr_result["confidence"]

                processing_metadata = {
                    "ocr_confidence": confidence,
                    "detected_language": ocr_result["language"],
                    "word_count": ocr_result["word_count"],
                    "page_count": ocr_result.get("page_count", 1),
                    "has_markdown": bool(content_markdown),
                    "chart_recognition": use_chart_recognition,
                    "orientation_classify": use_orientation_classify,
                    "unwarping": use_unwarping,
                }

                # Validate OCR confidence (T046)
                if confidence < MIN_OCR_CONFIDENCE:
                    logger.warning(
                        f"Low OCR confidence: {confidence:.2f} < {MIN_OCR_CONFIDENCE}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "low_ocr_confidence",
                            "message": f"OCR confidence too low ({confidence:.1%}). {input_type.title()} may be unclear or text is hard to read.",
                            "confidence": confidence,
                            "threshold": MIN_OCR_CONFIDENCE,
                            "extracted_text": extracted_content,
                            "extracted_markdown": content_markdown,
                            "fallback": "manual_edit",
                            "suggestions": [
                                f"Retake the {input_type} with better quality",
                                "Ensure text is in focus",
                                "Use the extracted text below and edit manually",
                                f"Try a different {input_type}"
                            ]
                        }
                    )

                # Warn if confidence is moderate (T047)
                if confidence < WARN_OCR_CONFIDENCE:
                    logger.warning(
                        f"Moderate OCR confidence: {confidence:.2f}"
                    )
                    processing_metadata["confidence_warning"] = True
                    processing_metadata["manual_review_recommended"] = True

                logger.info(
                    f"OCR completed: {ocr_result['word_count']} words, "
                    f"{processing_metadata['page_count']} pages, "
                    f"confidence: {confidence:.2f}, "
                    f"markdown: {processing_metadata['has_markdown']}"
                )

            finally:
                # Clean up temp file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        # Validate extracted content
        if not extracted_content or len(extracted_content.strip()) < MIN_CONTENT_LENGTH:
            error_detail = {
                "error": "content_too_short",
                "message": f"Extracted content is too short (minimum {MIN_CONTENT_LENGTH} characters)",
                "extracted_length": len(extracted_content.strip()) if extracted_content else 0,
                "minimum_required": MIN_CONTENT_LENGTH,
            }

            # Add specific guidance based on input type
            if input_type == "voice":
                error_detail["suggestions"] = [
                    "Ensure you spoke for at least a few seconds",
                    "Check microphone is working properly",
                    "Try recording again with more content"
                ]
            elif input_type == "image":
                error_detail["suggestions"] = [
                    "Ensure the image contains visible text",
                    "Check that text is not too small or blurry",
                    "Try a different image with clearer text"
                ]

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail
            )

        # AI processing (if enabled)
        categories = []
        summary = ""
        ai_metadata = {}
        ai_processing_status = 0  # Default: PENDING
        ai_error_message = None

        if auto_process:
            try:
                ai_processor = get_ai_processor()

                # Use Markdown content for AI processing if available (better structure)
                content_for_ai = content_markdown if content_markdown else extracted_content

                # Generate title
                title = await ai_processor.generate_title(
                    content_for_ai,
                    max_length=50,
                    language=language
                )

                # Process content for categories and summary
                ai_result = await ai_processor.process_content(
                    content_for_ai,
                    input_type=input_type,
                    language=language,
                    metadata=processing_metadata
                )

                categories = ai_result["categories"]
                summary = ai_result["summary"]
                ai_metadata = {
                    "ai_confidence": ai_result["confidence"],
                    "sentiment": ai_result["sentiment"],
                    "keywords": ai_result["keywords"],
                }

                # Mark AI processing as completed
                ai_processing_status = 2  # COMPLETED
                logger.info(f"AI processing completed: categories={categories}")

            except Exception as e:
                logger.error(f"AI processing failed: {e}")
                # Mark AI processing as failed
                ai_processing_status = 1  # FAILED
                ai_error_message = str(e)
                # Continue without AI processing
                title = extracted_content[:50] + ("..." if len(extracted_content) > 50 else "")
        else:
            # Generate simple title without AI
            title = extracted_content[:50] + ("..." if len(extracted_content) > 50 else "")
            # No AI processing requested
            ai_processing_status = 0  # PENDING (or could be None if never processed)

        # Serialize processing options for storage
        processing_options_json = None
        if input_type in ["image", "pdf"] and (use_chart_recognition or use_orientation_classify or use_unwarping):
            import json
            processing_options_json = json.dumps({
                "chart_recognition": use_chart_recognition,
                "orientation_classify": use_orientation_classify,
                "unwarping": use_unwarping,
            }, ensure_ascii=False)

        # Create database record
        new_record = InspirationRecord(
            title=title,
            content=extracted_content,
            content_markdown=content_markdown,  # Save Markdown content
            summary=summary if summary else None,
            input_type=input_type,
            category_tags=serialize_category_tags(categories) if categories else None,
            sync_status=0,  # Not synced
            ai_processing_status=ai_processing_status,
            ai_error_message=ai_error_message,
            version=1,
            # File paths
            audio_file_path=file_path if input_type == "voice" else None,
            image_file_path=file_path if input_type == "image" else None,
            pdf_file_path=file_path if input_type == "pdf" else None,
            # OCR/PDF metadata
            ocr_confidence=processing_metadata.get("ocr_confidence"),
            page_count=processing_metadata.get("page_count"),
            processing_options=processing_options_json,
        )

        db.add(new_record)
        await db.flush()  # Get ID without committing

        # Create sync queue entry
        sync_task = SyncQueue(
            record_id=new_record.id,
            operation=SyncOperation.CREATE,
            status=0,  # PENDING
            retry_count=0,
            max_retries=5,
            priority=0,  # NORMAL
        )

        db.add(sync_task)
        await db.commit()
        await db.refresh(new_record)

        logger.info(f"Record created: id={new_record.id}, title={new_record.title}")

        return new_record

    except HTTPException:
        raise

    except ExternalServiceException as e:
        logger.error(f"External service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to create record: {type(e).__name__}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create record: {str(e)}"
        )


@router.get("/{record_id}", response_model=InspirationRecordResponse)
async def get_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single inspiration record by ID
    """
    result = await db.execute(
        select(InspirationRecord).where(InspirationRecord.id == record_id)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record with ID {record_id} not found"
        )

    return record


@router.put("/{record_id}", response_model=InspirationRecordResponse)
async def update_record(
    record_id: int,
    record: InspirationRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing inspiration record with optimistic locking

    Updates are versioned to prevent concurrent modification conflicts.
    If the version doesn't match, a 409 Conflict is returned.
    """
    try:
        # Fetch existing record
        result = await db.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        existing_record = result.scalar_one_or_none()

        if not existing_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Record with ID {record_id} not found"
            )

        # Optimistic locking: check version
        if record.version and record.version != existing_record.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "version_conflict",
                    "message": "Record was modified by another process. Please refresh and try again.",
                    "current_version": existing_record.version,
                    "provided_version": record.version
                }
            )

        # Update fields (only if provided)
        update_data = record.model_dump(exclude_unset=True, exclude={"version"})

        for field, value in update_data.items():
            if hasattr(existing_record, field):
                setattr(existing_record, field, value)

        # Increment version and update timestamp
        existing_record.version += 1
        existing_record.updated_at = datetime.utcnow()

        # Create sync task for update
        sync_task = SyncQueue(
            record_id=record_id,
            operation=SyncOperation.UPDATE,
            status=0,  # PENDING
            retry_count=0,
            max_retries=5,
            priority=0,  # NORMAL
        )
        db.add(sync_task)

        await db.commit()
        await db.refresh(existing_record)

        logger.info(f"Record updated: id={record_id}, version={existing_record.version}")

        return existing_record

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update record {record_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update record: {str(e)}"
        )


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an inspiration record

    This performs a hard delete. The record and associated sync tasks
    will be permanently removed from the database.
    """
    try:
        # Fetch existing record
        result = await db.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        existing_record = result.scalar_one_or_none()

        if not existing_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Record with ID {record_id} not found"
            )

        # If record has a Notion page ID, create archive task
        if existing_record.notion_page_id:
            sync_task = SyncQueue(
                record_id=record_id,
                operation=SyncOperation.DELETE,
                status=0,  # PENDING
                retry_count=0,
                max_retries=5,
                priority=1,  # HIGH priority for deletions
            )
            db.add(sync_task)
            await db.commit()

            logger.info(
                f"Created delete sync task for record {record_id} "
                f"(notion_page_id={existing_record.notion_page_id})"
            )
        else:
            # No Notion sync needed, delete immediately
            await db.delete(existing_record)
            await db.commit()

            logger.info(f"Record deleted immediately: id={record_id}")

        return None

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to delete record {record_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete record: {str(e)}"
        )
