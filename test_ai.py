import asyncio
from app.adapters.resume_ai_adapter import ResumeAIAdapter
from app.config import settings
import time

async def test():
    print("Testing ResumeAIAdapter...")
    if not settings.openai_api_key:
        print("ERROR: OPENAI_API_KEY is not set in settings!")
        return

    ai = ResumeAIAdapter(api_key=settings.openai_api_key)
    start = time.time()
    try:
        res = await ai.tailor_resume(
            resume_text="I am a software engineer with Python experience.",
            job_description="We need a Cloud Platform Engineer with AWS and Python."
        )
        print("Success! Time taken:", time.time() - start, "seconds")
        print("Result length:", len(res))
    except Exception as e:
        print("Error during execution:", type(e).__name__, e)

if __name__ == "__main__":
    asyncio.run(test())
