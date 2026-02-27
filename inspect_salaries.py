import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from app.dependencies import _get_supabase_client
from app.adapters.supabase_adapter import SupabaseAdapter

async def inspect():
    print("Fetching all active jobs...")
    client = _get_supabase_client()
    db = SupabaseAdapter(client)
    
    jobs = await db.get_all_jobs_for_analytics()
    print(f"Found {len(jobs)} jobs.")
    
    print("\n--- Salary Ranges ---")
    for j in jobs:
        range_val = j.get('salary_range')
        if range_val:
            print(f"'{j.get('title')}': {range_val} (Type: {type(range_val)})")
        else:
            print(f"'{j.get('title')}': None")

if __name__ == "__main__":
    asyncio.run(inspect())
