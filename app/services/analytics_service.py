from datetime import datetime, timedelta
from typing import Any, List
from collections import Counter
import re

from app.ports.database_port import DatabasePort

class AnalyticsService:
    def __init__(self, db: DatabasePort):
        self.db = db

    async def get_market_stats(self) -> dict[str, Any]:
        """
        Aggregates market data from raw jobs.
        Returns:
            - total_jobs: int
            - top_skills: list[dict] {name, count}
            - salary_trends: list[dict] {role, avg_min, avg_max, count}
            - top_companies: list[dict] {name, count}
        """
        jobs = await self.db.get_all_jobs_for_analytics()
        
        if not jobs:
            return {
                "total_jobs": 0,
                "top_skills": [],
                "salary_trends": [],
                "top_companies": []
            }

        # 1. Total Jobs
        total_jobs = len(jobs)

        # 2. Extract Skills (Counter)
        all_skills = []
        for j in jobs:
            if j.get('skills_required'):
                # Normalize: lowercase, strip
                skills = [s.lower().strip() for s in j['skills_required']]
                all_skills.extend(skills)
        
        skill_counts = Counter(all_skills).most_common(10)
        top_skills = [{"name": s[0].title(), "count": s[1]} for s in skill_counts]

        # 3. Companies
        companies = [j['company_name'] for j in jobs if j.get('company_name')]
        company_counts = Counter(companies).most_common(5)
        top_companies = [{"name": c[0], "count": c[1]} for c in company_counts]

        # 4. Salary & Roles (Simple grouping)
        # We'll group by "Normalized Title" to get averages
        role_stats = {} # { "Senior Engineer": [min_sals...] }
        
        for j in jobs:
            title = j.get('title', 'Unknown')
            # Parse salary_range (e.g. "$100k - $150k" or "100-150")
            s_min, s_max = None, None
            if j.get('salary_range'):
                # Basic parsing: find all numbers, take first two
                nums = re.findall(r'(\d+)', str(j['salary_range']).replace(',', ''))
                if len(nums) >= 2:
                    try:
                        s_min = int(nums[0])
                        s_max = int(nums[1])
                        # Handle "k" suffix logic if needed, but for now assume raw or simple
                        if 'k' in str(j['salary_range']).lower() and s_max < 1000:
                            s_min *= 1000
                            s_max *= 1000
                    except:
                        pass
            
            # Simple normalization
            norm_title = self._normalize_title(title)
            
            if s_min and s_max:
                if norm_title not in role_stats:
                    role_stats[norm_title] = {'min': [], 'max': [], 'count': 0}
                role_stats[norm_title]['min'].append(s_min)
                role_stats[norm_title]['max'].append(s_max)
                role_stats[norm_title]['count'] += 1

        salary_trends = []
        for role, stats in role_stats.items():
            if stats['count'] >= 1: # Include even single data points for now
                avg_min = sum(stats['min']) / len(stats['min'])
                avg_max = sum(stats['max']) / len(stats['max'])
                salary_trends.append({
                    "role": role,
                    "avg_min": int(avg_min),
                    "avg_max": int(avg_max),
                    "count": stats['count']
                })
        
        # Sort by count desc
        salary_trends.sort(key=lambda x: x['count'], reverse=True)
        salary_trends = salary_trends[:8] # Top 8 roles

        # 5. Work Style Distribution
        work_styles = Counter()
        for j in jobs:
            loc = (j.get('location') or '').lower()
            title = (j.get('title') or '').lower()
            desc = (j.get('description') or '').lower()
            
            if 'remote' in loc or 'remote' in title:
                work_styles['Remote'] += 1
            elif 'hybrid' in loc or 'hybrid' in title:
                work_styles['Hybrid'] += 1
            else:
                work_styles['On-site'] += 1
        
        work_style_stats = [{"name": k, "value": v} for k, v in work_styles.items()]

        # 6. Experience Levels
        experience = Counter()
        for j in jobs:
            title = (j.get('title') or '').lower()
            if 'senior' in title or 'sr.' in title or 'lead' in title or 'principal' in title:
                experience['Senior/Lead'] += 1
            elif 'junior' in title or 'jr.' in title or 'entry' in title or 'graduate' in title:
                experience['Junior/Entry'] += 1
            elif 'mid' in title or 'intermediate' in title:
                experience['Mid-Level'] += 1
            elif 'intern' in title:
                experience['Internship'] += 1
            else:
                experience['Not Specified'] += 1 # Or group into Mid? Let's keep distinct

        experience_stats = [{"subject": k, "A": v, "fullMark": total_jobs} for k, v in experience.items() if v > 0]

        return {
            "total_jobs": total_jobs,
            "top_skills": top_skills,
            "salary_trends": salary_trends,
            "top_companies": top_companies,
            "work_styles": work_style_stats,
            "experience_levels": experience_stats
        }

    def _normalize_title(self, title: str) -> str:
        """
        Simplifies job titles for grouping.
        E.g. "Senior Backend Engineer (Remote)" -> "Backend Engineer"
        """
        t = title.lower()
        # Remove contents in parens
        t = re.sub(r'\(.*?\)', '', t)
        
        if 'manager' in t: return 'Manager'
        if 'director' in t: return 'Director'
        if 'intern' in t: return 'Intern'
        
        # Tech roles
        if 'full stack' in t or 'full-stack' in t: return 'Full Stack Developer'
        if 'backend' in t or 'back end' in t: return 'Backend Engineer'
        if 'frontend' in t or 'front end' in t: return 'Frontend Engineer'
        if 'data scientist' in t: return 'Data Scientist'
        if 'data engineer' in t: return 'Data Engineer'
        if 'devops' in t or 'sre' in t: return 'DevOps / SRE'
        if 'product' in t: return 'Product Manager'
        if 'sales' in t: return 'Sales'
        
        return title.strip().title()
