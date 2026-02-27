from typing import Any
from uuid import UUID
from datetime import datetime, timezone

from app.domain.enums import MockInterviewStatus
from app.domain.models import MockScorecard
from app.ports.database_port import DatabasePort
from app.ports.ai_port import AIPort

class MockInterviewService:
    """
    Orchestrates the Mock Interview flow:
    1. Start interview (selects 5 questions from job enrichment).
    2. Submit answers sequentially.
    3. Finalize with AI evaluation.
    4. Request expert review.
    """

    def __init__(self, db: DatabasePort, ai: AIPort) -> None:
        self._db = db
        self._ai = ai

    async def start_interview(self, user_id: str, job_id: str) -> dict[str, Any]:
        """Initialize a new mock interview session."""
        job = await self._db.get_job(job_id)
        if not job:
            raise ValueError("Job not found")

        # Ensure job has prep questions
        questions = job.get("prep_guide_generated")
        if not questions:
            raise ValueError("Job has no prep questions yet. AI enrichment is still processing.")

        # Create record
        data = {
            "user_id": user_id,
            "job_id": job_id,
            "transcript": [],
            "status": MockInterviewStatus.IN_PROGRESS,
        }
        return await self._db.create_mock_interview(data)

    async def submit_answers(self, interview_id: str, answers: list[str]) -> dict[str, Any]:
        """
        Submit all 5 answers at once for evaluation.
        (Simplified flow for V1 scorecard dashboard)
        """
        interview = await self._db.get_mock_interview(interview_id)
        if not interview:
            raise ValueError("Interview not found")

        job = await self._db.get_job(str(interview["job_id"]))
        prep_questions = job.get("prep_guide_generated", [])

        # Build transcript
        transcript = []
        for i, ans in enumerate(answers):
            q_text = "Question"
            if i < len(prep_questions):
                q = prep_questions[i]
                q_text = q.get("question") if isinstance(q, dict) else str(q)
            
            transcript.append({"role": "assistant", "content": q_text})
            transcript.append({"role": "user", "content": ans})

        # Evaluate via AI
        scorecard = await self._ai.evaluate_mock_interview(
            transcript=transcript,
            job_description=job.get("description_raw", "")
        )

        # Update record
        update_data = {
            "transcript": transcript,
            "ai_scorecard": scorecard.model_dump(),
            "status": MockInterviewStatus.COMPLETED
        }
        await self._db.update_mock_interview(interview_id, update_data)
        
        return await self._db.get_mock_interview(interview_id)

    async def request_review(self, interview_id: str) -> None:
        """Mark an interview as pending expert review."""
        await self._db.update_mock_interview(
            interview_id, 
            {"status": MockInterviewStatus.PENDING_REVIEW}
        )

    async def list_user_interviews(self, user_id: str) -> list[dict[str, Any]]:
        return await self._db.list_user_mock_interviews(user_id)

    async def get_interview_details(self, interview_id: str) -> dict[str, Any]:
        interview = await self._db.get_mock_interview(interview_id)
        if not interview:
            raise ValueError("Interview not found")
        return interview
