from app.ports.ai_port import AIPort

class ResumeTailorService:
    def __init__(self, ai: AIPort):
        self.ai = ai

    async def tailor_resume(self, resume_text: str, job_description: str) -> str:
        """
        Rewrites the resume to better match the job description.
        """
        return await self.ai.tailor_resume(resume_text, job_description)
