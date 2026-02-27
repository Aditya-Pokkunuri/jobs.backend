"""
Experience filter utility for the scraper module.
Filters jobs to include only fresher / 0-2 years experience roles.
"""

import re

# Keywords that strongly indicate an entry-level role
ENTRY_LEVEL_KEYWORDS = {
    "analyst",
    "associate",
    "intern",
    "trainee",
    "fresher",
    "graduate",
    "entry",
    "junior",
    "apprentice",
}

# Keywords that strongly indicate a senior role (reject these)
SENIOR_KEYWORDS = {
    "senior",
    "manager",
    "director",
    "vp",
    "principal",
    "lead",
    "head",
    "architect",
    "partner",
    "chief",
}


def is_entry_level(title: str, experience_text: str = "") -> bool:
    """
    Returns True if the job is likley for a fresher or 0-2 years experience.
    Rejects senior roles based on title keywords.
    Accepts roles with 0-2 years experience mentioned or entry-level keywords.
    """
    title_lower = title.lower()

    # 1. Reject if title contains senior keywords
    # Exception: "Senior Analyst" might be okay in some contexts, but usually >2 yrs.
    # For now, we'll be strict to avoid noise.
    if any(kw in title_lower for kw in SENIOR_KEYWORDS):
        return False

    # 2. Accept if title contains entry-level keywords
    if any(kw in title_lower for kw in ENTRY_LEVEL_KEYWORDS):
        return True

    # 3. Check experience text for 0-2 year range using regex
    # Matches: "0-2 years", "0 - 1 year", "1 year", "fresher", "entry level"
    # Does NOT match: "3-5 years", "5+ years"
    
    # "0-X years" where X is 0, 1, or 2
    if re.search(r'\b0\s*[-–]\s*[0-2]\s*years?\b', experience_text, re.I):
        return True
    
    # "1 year", "1-2 years"
    if re.search(r'\b1\s*[-–]?\s*[1-2]?\s*years?\b', experience_text, re.I):
        return True
        
    # "Fresher" or "Entry Level" explicitly mentioned
    if re.search(r'\bfresher|entry.?level\b', experience_text, re.I):
        return True

    # Default to True to allow all jobs for now (User request: "display them")
    return True
