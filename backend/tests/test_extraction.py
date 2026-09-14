"""
Unit tests for AI transcript extraction service, prompt management, and schema validation.
"""
import json
import pytest
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock

from app.schemas.extraction import (
    ExtractedAbsenceInfo,
    AbsenceCategoryEnum,
    ExtractionConfidence
)
from app.services.extraction_provider import ExtractionError
from app.services.prompt_manager import ExtractionPromptManager, PromptVersion
from app.services.openai_extractor import OpenAIExtractor
from app.services.anthropic_extractor import AnthropicExtractor
from app.services.ai_service import AIService


# ============================================================================
# Realistic Transcript Fixtures
# ============================================================================

TRANSCRIPT_FEVER = """
ASSISTANT: Hello, this is the attendance assistant calling from the college regarding Alex Rivera's absence on September 12th. May I please speak with a parent or guardian?
PARENT: Yes, this is Alex's father speaking.
ASSISTANT: Thank you. We're calling because Alex was marked absent today. Were you aware of this absence?
PARENT: Yes, I am. He woke up with a high fever, around 102, so I told him to stay home and rest.
ASSISTANT: I understand. When do you expect Alex to return to classes?
PARENT: He should be back in about two days, probably by Monday if the fever breaks.
ASSISTANT: Just to confirm, Alex was absent today due to a fever and is expected back on Monday in about two days. Is that correct?
PARENT: Yes, that is correct.
ASSISTANT: Thank you for the information. We hope Alex feels better soon. Have a good day.
"""

TRANSCRIPT_FAMILY_EVENT = """
ASSISTANT: Hello, this is the attendance assistant calling from the college regarding Maya Patel's absence on September 12th. May I please speak with a parent or guardian?
PARENT: Hello, this is Maya's mother.
ASSISTANT: Thank you, Mrs. Patel. We're calling to follow up on Maya's absence today.
PARENT: Yes, we are out of town attending her older brother's wedding this weekend.
ASSISTANT: Wonderful! When do you expect Maya to be back in classes?
PARENT: We'll be traveling back on Sunday, so she will definitely be back on Monday morning.
ASSISTANT: So Maya is absent for a family wedding and will return on Monday. Is that right?
PARENT: Exactly, thank you.
ASSISTANT: Thank you, congratulations to your family, and have a safe trip back!
"""

TRANSCRIPT_TRANSPORTATION = """
ASSISTANT: Hello, this is the attendance assistant calling from the college regarding Jordan Lee's absence on September 12th. May I please speak with a parent or guardian?
PARENT: Hi, this is Jordan's mom.
ASSISTANT: Thank you. We're calling regarding Jordan's absence from classes today.
PARENT: Oh yes, our car broke down on the highway this morning and the tow truck took three hours. Jordan couldn't get a ride to campus in time for classes.
ASSISTANT: I'm sorry to hear that. Will Jordan be attending tomorrow?
PARENT: Yes, the car is at the shop and my husband will drive him tomorrow morning. Just a 1 day issue.
ASSISTANT: Thank you for letting us know. We'll update the attendance records.
"""

TRANSCRIPT_PARENT_REFUSES = """
ASSISTANT: Hello, this is the attendance assistant calling from the college regarding Sam Taylor's absence on September 12th. May I please speak with a parent or guardian?
PARENT: Yeah, I'm Sam's guardian. Why are you calling?
ASSISTANT: We're calling because Sam was marked absent today. Could you share the reason for the absence?
PARENT: That is none of your business. It's a private matter and I don't need to explain myself to an automated system.
ASSISTANT: I understand your concern. We just need to ensure the student is safe and accounted for.
PARENT: He's fine, but I'm not answering any of your questions. Don't call me again.
ASSISTANT: Thank you for your time. Have a good day.
"""

TRANSCRIPT_UNCLEAR_RESPONSE = """
ASSISTANT: Hello, this is the attendance assistant calling from the college regarding Chris Evans's absence on September 12th. May I please speak with a parent or guardian?
PARENT: Uh... yeah, who is this?
ASSISTANT: This is the college attendance assistant calling about Chris's absence today.
PARENT: Oh, right, yeah... uh... things are just really hectic today. You know, stuff happened and... yeah, they just couldn't make it.
ASSISTANT: I understand. Is Chris feeling unwell or is there an expected date for return?
PARENT: I don't know, maybe tomorrow? Or next week? We'll see how things go.
ASSISTANT: Thank you for your time.
"""

TRANSCRIPT_NO_PARENT_VOICEMAIL = """
ASSISTANT: Hello, this is the attendance assistant calling from the college regarding Taylor Brooks's absence on September 12th.
VOICEMAIL: You have reached the voicemail of 555-0199. Please leave a message after the tone. *BEEP*
ASSISTANT: Hello, this is an automated message from the college attendance office regarding Taylor Brooks. Please call us back at 555-0100 to confirm this absence. Thank you.
"""

TRANSCRIPT_MULTIPLE_REASONS = """
ASSISTANT: Hello, this is the attendance assistant calling from the college regarding Riley Davis's absence on September 12th. May I please speak with a parent or guardian?
PARENT: Yes, Riley's mom here.
ASSISTANT: Thank you. We're calling about Riley's absence today.
PARENT: Well, it's been a crazy morning. First, Riley woke up with a migraine and wasn't feeling good at all. Then our car wouldn't start either. On top of that, we have my grandmother's doctor appointment this afternoon that I need to take her to. So with the migraine and no car, she just couldn't make it today.
ASSISTANT: I understand, that sounds like a challenging day. When do you expect Riley back?
PARENT: The migraine usually clears up in a day, and the car will be jumped by this evening, so she should be back tomorrow.
ASSISTANT: Thank you for confirming that Riley should return tomorrow. Take care.
"""


# ============================================================================
# Pydantic Schema Validation Tests
# ============================================================================

class TestExtractedAbsenceInfoSchema:
    """Test schema validation rules and behavior."""

    def test_valid_medical_extraction(self):
        """Test a clean medical extraction passes validation."""
        info = ExtractedAbsenceInfo(
            reason="High fever and flu symptoms",
            category=AbsenceCategoryEnum.MEDICAL,
            duration="2-3 days",
            expected_return="2026-09-15",
            parent_confirmed=True,
            follow_up_required=False,
            confidence_score=0.95,
            notes="Doctor appointment scheduled",
            parent_statement="He has a high fever",
            call_outcome="completed"
        )
        assert info.category == AbsenceCategoryEnum.MEDICAL
        assert info.confidence_score == 0.95
        assert info.confidence == 0.95
        assert info.confidence_level == ExtractionConfidence.HIGH
        assert info.parent_confirmed is True
        assert info.follow_up_required is False
        assert info.expected_return == "2026-09-15"
        assert info.expected_return_date == date(2026, 9, 15)

    def test_canonical_dictionary_output(self):
        """Test the canonical expected dictionary representation."""
        info = ExtractedAbsenceInfo(
            reason="Severe migraine",
            category=AbsenceCategoryEnum.MEDICAL,
            duration="1 day",
            expected_return="tomorrow",
            parent_confirmed=True,
            follow_up_required=False,
            confidence_score=0.92,
            call_outcome="completed"
        )
        canonical = info.to_canonical_dict()
        assert canonical == {
            "reason": "Severe migraine",
            "category": "medical",
            "duration": "1 day",
            "expected_return": "tomorrow",
            "parent_confirmed": True,
            "follow_up_required": False,
            "confidence": 0.92
        }

    def test_low_confidence_auto_flags_followup(self):
        """Test that low confidence (<0.85) automatically sets follow_up_required to True."""
        info = ExtractedAbsenceInfo(
            reason="Unclear mumbling",
            category=AbsenceCategoryEnum.UNKNOWN,
            parent_confirmed=False,
            follow_up_required=False,  # Even if set to False, validator will force True
            confidence_score=0.60,
            call_outcome="completed"
        )
        assert info.confidence_score == 0.60
        assert info.confidence_level == ExtractionConfidence.LOW
        assert info.follow_up_required is True

    def test_very_low_confidence_classification(self):
        """Test confidence level buckets."""
        info = ExtractedAbsenceInfo(
            confidence_score=0.30,
            category=AbsenceCategoryEnum.UNKNOWN,
            parent_confirmed=False,
            follow_up_required=True,
            call_outcome="no_answer"
        )
        assert info.confidence_level == ExtractionConfidence.VERY_LOW

    def test_null_fields_preserved_not_invented(self):
        """Test unknown fields default to None and are not invented."""
        info = ExtractedAbsenceInfo(
            category=AbsenceCategoryEnum.UNKNOWN,
            parent_confirmed=False,
            follow_up_required=True,
            confidence_score=0.0,
            call_outcome="voicemail"
        )
        assert info.reason is None
        assert info.duration is None
        assert info.expected_return is None
        assert info.expected_return_date is None
        assert info.notes is None
        assert info.parent_statement is None

    def test_refusal_notes_auto_flags_followup(self):
        """Test that parent refusal in notes forces follow-up."""
        info = ExtractedAbsenceInfo(
            category=AbsenceCategoryEnum.UNKNOWN,
            parent_confirmed=False,
            follow_up_required=False,
            confidence_score=0.90,  # High score, but parent refused
            notes="Parent refused to answer questions",
            call_outcome="completed"
        )
        assert info.follow_up_required is True

    def test_confidence_score_bounds(self):
        """Test confidence score validation bounds (0.0 to 1.0)."""
        with pytest.raises(Exception):
            ExtractedAbsenceInfo(
                confidence_score=1.5,  # > 1.0 invalid
                category=AbsenceCategoryEnum.UNKNOWN,
                parent_confirmed=False,
                follow_up_required=True,
                call_outcome="completed"
            )

        with pytest.raises(Exception):
            ExtractedAbsenceInfo(
                confidence_score=-0.1,  # < 0.0 invalid
                category=AbsenceCategoryEnum.UNKNOWN,
                parent_confirmed=False,
                follow_up_required=True,
                call_outcome="completed"
            )

    def test_confidence_threshold_boundaries(self):
        """Regression: confidence_level must reflect confidence_score at all threshold boundaries."""
        cases = [
            (0.95, ExtractionConfidence.HIGH),
            (0.85, ExtractionConfidence.HIGH),    # boundary: >= 0.85
            (0.84, ExtractionConfidence.MEDIUM),
            (0.70, ExtractionConfidence.MEDIUM),  # boundary: >= 0.70
            (0.69, ExtractionConfidence.LOW),
            (0.50, ExtractionConfidence.LOW),     # boundary: >= 0.50
            (0.49, ExtractionConfidence.VERY_LOW),
            (0.0, ExtractionConfidence.VERY_LOW),
        ]
        for score, expected in cases:
            info = ExtractedAbsenceInfo(
                confidence_score=score,
                category=AbsenceCategoryEnum.UNKNOWN,
                parent_confirmed=False,
                follow_up_required=False,
                call_outcome="completed",
            )
            assert info.confidence_level == expected, f"score {score} -> {info.confidence_level}"

    def test_high_confidence_explicit_followup_preserved(self):
        """Regression: explicit follow_up_required=True is preserved at high confidence."""
        info = ExtractedAbsenceInfo(
            reason="Stomach flu",
            category=AbsenceCategoryEnum.MEDICAL,
            confidence_score=0.95,
            parent_confirmed=True,
            follow_up_required=True,  # explicitly requested follow-up
            call_outcome="completed",
        )
        assert info.confidence_level == ExtractionConfidence.HIGH
        assert info.follow_up_required is True


# ============================================================================
# Prompt Management Tests
# ============================================================================

class TestPromptManager:
    """Test prompt builder, rules, and versioning."""

    def test_system_prompt_contains_guardrails(self):
        prompt = ExtractionPromptManager.get_system_prompt()
        assert "NEVER INVENT INFORMATION" in prompt
        assert "DO NOT DIAGNOSE MEDICAL CONDITIONS" in prompt
        assert "PRESERVE VERBATIM STATEMENTS" in prompt

    def test_build_extraction_prompt_with_context(self):
        built = ExtractionPromptManager.build_extraction_prompt(
            transcript="SAMPLE TRANSCRIPT",
            student_name="Alex Rivera",
            absence_date=date(2026, 9, 12),
            context={"grade_level": "Sophomore", "student_id": "ST123"}
        )
        assert "Alex Rivera" in built
        assert "2026-09-12" in built
        assert "Sophomore" in built
        assert "SAMPLE TRANSCRIPT" in built

    def test_openai_and_anthropic_schemas_available(self):
        fn_schema = ExtractionPromptManager.get_openai_function_schema()
        assert fn_schema["name"] == "record_absence_information"
        assert "category" in fn_schema["parameters"]["properties"]

        anthropic_schema = ExtractionPromptManager.get_anthropic_json_schema()
        assert "JSON object" in anthropic_schema


# ============================================================================
# Extraction Provider Tests with Mock LLM Responses
# ============================================================================

class TestExtractionCases:
    """Test various extraction scenarios with mocked LLM output."""

    @pytest.mark.asyncio
    async def test_extraction_fever(self):
        """Test Case 1: Fever / Medical illness."""
        mock_response = {
            "reason": "High fever, around 102",
            "category": "medical",
            "duration": "2 days",
            "expected_return": "Monday",
            "expected_return_date": "2026-09-15",
            "parent_confirmed": True,
            "follow_up_required": False,
            "confidence_score": 0.95,
            "notes": "Parent told student to stay home and rest",
            "parent_statement": "He woke up with a high fever, around 102",
            "call_outcome": "completed"
        }

        extractor = OpenAIExtractor(api_key="test-key")
        with patch.object(extractor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_message = MagicMock()
            mock_func = MagicMock()
            mock_func.arguments = str(mock_response).replace("'", '"').replace("True", "true").replace("False", "false")
            mock_message.function_call = mock_func
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_create.return_value = MagicMock(choices=[mock_choice])

            result = await extractor.extract_absence_info(
                transcript=TRANSCRIPT_FEVER,
                student_name="Alex Rivera",
                absence_date=date(2026, 9, 12)
            )

            assert result.category == AbsenceCategoryEnum.MEDICAL
            assert "fever" in result.reason.lower()
            assert result.parent_confirmed is True
            assert result.confidence_score >= 0.85
            assert result.confidence_level == ExtractionConfidence.HIGH
            assert result.follow_up_required is False

    @pytest.mark.asyncio
    async def test_extraction_family_event(self):
        """Test Case 2: Family wedding / event."""
        mock_response = {
            "reason": "Out of town attending brother's wedding",
            "category": "family",
            "duration": "Weekend / through Sunday",
            "expected_return": "Monday morning",
            "expected_return_date": "2026-09-15",
            "parent_confirmed": True,
            "follow_up_required": False,
            "confidence_score": 0.95,
            "notes": "Traveling back on Sunday",
            "parent_statement": "We are out of town attending her older brother's wedding this weekend",
            "call_outcome": "completed"
        }

        extractor = OpenAIExtractor(api_key="test-key")
        with patch.object(extractor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_message = MagicMock()
            mock_func = MagicMock()
            mock_func.arguments = json.dumps(mock_response)
            mock_message.function_call = mock_func
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_create.return_value = MagicMock(choices=[mock_choice])

            result = await extractor.extract_absence_info(
                transcript=TRANSCRIPT_FAMILY_EVENT,
                student_name="Maya Patel",
                absence_date=date(2026, 9, 12)
            )

            assert result.category == AbsenceCategoryEnum.FAMILY
            assert "wedding" in result.reason.lower()
            assert result.parent_confirmed is True
            assert result.follow_up_required is False

    @pytest.mark.asyncio
    async def test_extraction_transportation_problem(self):
        """Test Case 3: Car breakdown / transportation issue."""
        mock_response = {
            "reason": "Car broke down on the highway, tow truck took three hours",
            "category": "transportation",
            "duration": "1 day",
            "expected_return": "tomorrow morning",
            "expected_return_date": "2026-09-13",
            "parent_confirmed": True,
            "follow_up_required": False,
            "confidence_score": 0.90,
            "notes": "Husband will drive student tomorrow",
            "parent_statement": "Our car broke down on the highway this morning",
            "call_outcome": "completed"
        }

        extractor = OpenAIExtractor(api_key="test-key")
        with patch.object(extractor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_message = MagicMock()
            mock_func = MagicMock()
            mock_func.arguments = str(mock_response).replace("'", '"').replace("True", "true").replace("False", "false")
            mock_message.function_call = mock_func
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_create.return_value = MagicMock(choices=[mock_choice])

            result = await extractor.extract_absence_info(
                transcript=TRANSCRIPT_TRANSPORTATION,
                student_name="Jordan Lee",
                absence_date=date(2026, 9, 12)
            )

            assert result.category == AbsenceCategoryEnum.TRANSPORTATION
            assert "car" in result.reason.lower() or "broke down" in result.reason.lower()
            assert result.duration == "1 day"

    @pytest.mark.asyncio
    async def test_extraction_parent_refuses(self):
        """Test Case 4: Parent refuses to provide a reason."""
        mock_response = {
            "reason": None,
            "category": "unknown",
            "duration": None,
            "expected_return": None,
            "expected_return_date": None,
            "parent_confirmed": True,
            "follow_up_required": True,
            "confidence_score": 0.40,
            "notes": "Parent explicitly refused to provide reason, stated private matter",
            "parent_statement": "That is none of your business. It's a private matter",
            "call_outcome": "completed"
        }

        extractor = OpenAIExtractor(api_key="test-key")
        with patch.object(extractor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_message = MagicMock()
            mock_func = MagicMock()
            mock_func.arguments = json.dumps(mock_response)
            mock_message.function_call = mock_func
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_create.return_value = MagicMock(choices=[mock_choice])

            result = await extractor.extract_absence_info(
                transcript=TRANSCRIPT_PARENT_REFUSES,
                student_name="Sam Taylor",
                absence_date=date(2026, 9, 12)
            )

            assert result.reason is None
            assert result.category == AbsenceCategoryEnum.UNKNOWN
            assert result.follow_up_required is True
            assert result.confidence_score < 0.50
            assert result.confidence_level == ExtractionConfidence.VERY_LOW

    @pytest.mark.asyncio
    async def test_extraction_unclear_response(self):
        """Test Case 5: Vague or unclear parent response."""
        mock_response = {
            "reason": "Things are hectic, stuff happened",
            "category": "unknown",
            "duration": None,
            "expected_return": "maybe tomorrow or next week",
            "expected_return_date": None,
            "parent_confirmed": True,
            "follow_up_required": True,
            "confidence_score": 0.55,
            "notes": "Parent was very vague about reason and return date",
            "parent_statement": "Stuff happened and they just couldn't make it",
            "call_outcome": "completed"
        }

        extractor = OpenAIExtractor(api_key="test-key")
        with patch.object(extractor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_message = MagicMock()
            mock_func = MagicMock()
            mock_func.arguments = json.dumps(mock_response)
            mock_message.function_call = mock_func
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_create.return_value = MagicMock(choices=[mock_choice])

            result = await extractor.extract_absence_info(
                transcript=TRANSCRIPT_UNCLEAR_RESPONSE,
                student_name="Chris Evans",
                absence_date=date(2026, 9, 12)
            )

            assert result.follow_up_required is True
            assert result.confidence_score < 0.70
            assert result.confidence_level in [ExtractionConfidence.LOW, ExtractionConfidence.VERY_LOW]

    @pytest.mark.asyncio
    async def test_extraction_no_parent_voicemail(self):
        """Test Case 6: Voicemail / no parent reached."""
        mock_response = {
            "reason": None,
            "category": "unknown",
            "duration": None,
            "expected_return": None,
            "expected_return_date": None,
            "parent_confirmed": False,
            "follow_up_required": True,
            "confidence_score": 0.0,
            "notes": "Reached voicemail, left automated callback message",
            "parent_statement": None,
            "call_outcome": "voicemail"
        }

        extractor = OpenAIExtractor(api_key="test-key")
        with patch.object(extractor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_message = MagicMock()
            mock_func = MagicMock()
            mock_func.arguments = json.dumps(mock_response)
            mock_message.function_call = mock_func
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_create.return_value = MagicMock(choices=[mock_choice])

            result = await extractor.extract_absence_info(
                transcript=TRANSCRIPT_NO_PARENT_VOICEMAIL,
                student_name="Taylor Brooks",
                absence_date=date(2026, 9, 12)
            )

            assert result.parent_confirmed is False
            assert result.confidence_score == 0.0
            assert result.confidence_level == ExtractionConfidence.VERY_LOW
            assert result.call_outcome == "voicemail"
            assert result.follow_up_required is True

    @pytest.mark.asyncio
    async def test_extraction_multiple_reasons(self):
        """Test Case 7: Parent gives multiple reasons (migraine + car trouble + family appointment)."""
        mock_response = {
            "reason": "Migraine headache and car wouldn't start",
            "category": "medical",
            "duration": "1 day",
            "expected_return": "tomorrow",
            "expected_return_date": "2026-09-13",
            "parent_confirmed": True,
            "follow_up_required": False,
            "confidence_score": 0.90,
            "notes": "Parent cited migraine as primary reason plus car issue and family doctor appointment",
            "parent_statement": "Riley woke up with a migraine and wasn't feeling good at all. Then our car wouldn't start either.",
            "call_outcome": "completed"
        }

        extractor = OpenAIExtractor(api_key="test-key")
        with patch.object(extractor.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_message = MagicMock()
            mock_func = MagicMock()
            mock_func.arguments = json.dumps(mock_response)
            mock_message.function_call = mock_func
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_create.return_value = MagicMock(choices=[mock_choice])

            result = await extractor.extract_absence_info(
                transcript=TRANSCRIPT_MULTIPLE_REASONS,
                student_name="Riley Davis",
                absence_date=date(2026, 9, 12)
            )

            assert result.parent_confirmed is True
            assert "migraine" in result.reason.lower()
            assert result.expected_return is not None

    @pytest.mark.asyncio
    async def test_anthropic_extractor_with_markdown_fence(self):
        """Test Anthropic Claude extractor correctly parses markdown fenced JSON."""
        mock_content = """```json
{
    "reason": "Severe strep throat",
    "category": "medical",
    "duration": "3 days",
    "expected_return": "Thursday",
    "expected_return_date": "2026-09-17",
    "parent_confirmed": true,
    "follow_up_required": false,
    "confidence_score": 0.94,
    "notes": "Parent took student to urgent care",
    "parent_statement": "He was diagnosed with strep throat this morning",
    "call_outcome": "completed"
}
```"""
        extractor = AnthropicExtractor(api_key="test-key")
        with patch.object(extractor.client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_block = MagicMock()
            mock_block.text = mock_content
            mock_create.return_value = MagicMock(content=[mock_block])

            result = await extractor.extract_absence_info(
                transcript="ASSISTANT: Hello... PARENT: He has strep throat",
                student_name="Jordan Bell",
                absence_date=date(2026, 9, 12)
            )

            assert result.category == AbsenceCategoryEnum.MEDICAL
            assert result.parent_confirmed is True
            assert result.confidence_score == 0.94
            assert result.follow_up_required is False

    @pytest.mark.asyncio
    async def test_ai_service_fallback_on_error(self):
        """Test that AIService returns a safe fallback object when provider errors."""
        mock_provider = AsyncMock()
        mock_provider.get_provider_name.return_value = "mock"
        mock_provider.extract_absence_info.side_effect = ExtractionError("Network connection timeout")

        service = AIService(provider=mock_provider)
        result = await service.extract_absence_info(
            transcript="some text",
            student_name="Test Student",
            absence_date=date(2026, 9, 12)
        )

        assert result.category == AbsenceCategoryEnum.UNKNOWN
        assert result.confidence_score == 0.0
        assert result.follow_up_required is True
        assert "Extraction error" in result.notes
