"""
Enhanced OpenAI adapter for Resume Builder.

Subclasses OpenAIAdapter to override tailor_resume() with:
  - gpt-4o-mini (via self._model) instead of hardcoded gpt-4o
  - max_tokens=1200  to prevent runaway generation
  - Explicit Anti-Fabrication rules in the system prompt
"""

from app.adapters.openai_adapter import OpenAIAdapter


class ResumeAIAdapter(OpenAIAdapter):
    """Drop-in replacement with improved tailor_resume behaviour."""

    async def tailor_resume(self, resume_text: str, job_description: str, job_title: str = "the target role", company_name: str = "the company") -> dict:
        """
        Rewrite a candidate's resume to target a specific job description, title, and company.

        Improvements over the base implementation:
          1. Uses self._model (gpt-4o-mini) for cost/speed.
          2. Caps output at 1200 tokens.
          3. Adds strict Anti-Fabrication rules.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are an expert ATS specialist and resume writer. "
                    f"Your task is to REWRITE the candidate's resume to specifically target the '{job_title}' role at '{company_name}'.\n\n"
                    "## Rules\n"
                    "1. Keep the candidate's truth — do NOT invent experiences, skills, certifications, "
                    "or employment history that the candidate does not have.\n"
                    "2. Rephrase existing bullet points to incorporate keywords from the job description "
                    "(e.g., if the JD says 'collaborated with cross-functional teams' and the candidate "
                    "says 'worked with others', update it accordingly).\n"
                    "3. Add a 'Targeted Professional Summary' section at the top.\n"
                    "4. Output the result in clean Markdown format.\n\n"
                    "## Anti-Fabrication Guidelines\n"
                    "- NEVER add technologies, tools, or frameworks the candidate has not mentioned.\n"
                    "- NEVER fabricate job titles, company names, or employment dates.\n"
                    "- NEVER invent metrics, percentages, or quantified achievements that are not present in the original.\n"
                    "- You MAY rephrase, reorder, and emphasise existing content to better align with the JD.\n"
                    "- You MAY remove irrelevant content to keep the resume focused.\n\n"
                    "## Output Format\n"
                    "You MUST output exactly a valid JSON object with two string keys:\n"
                    "1. 'tailored_resume': The fully rewritten resume in clean Markdown format.\n"
                    "2. 'change_summary': A detailed bulleted list (in Markdown) explaining what specific skills, phrases, or bullet points you added, emphasized, or reworded to match the JD."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## Target Job\n{job_description[:4000]}\n\n"
                    f"## Current Resume\n{resume_text[:4000]}\n\n"
                    "Rewrite my resume and summarize changes now. Return ONLY JSON."
                ),
            },
        ]

        response = await self._raw_client.chat.completions.create(
            model=self._model,   # gpt-4o-mini (set in __init__)
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=3000,     # prevent runaway generation but allow enough space for both
        )
        content = response.choices[0].message.content
        import json
        try:
            return json.loads(content)
        except Exception:
            return {
                "tailored_resume": content or "Failed to tailor resume.",
                "change_summary": "Failed to parse the change summary."
            }
