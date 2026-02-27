from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from app.ports.database_port import DatabasePort
from app.ports.ai_port import AIPort
from app.dependencies import get_db, get_ai_service
from app.services.auth_service import get_current_user
from app.agents.blog_agent import BlogAgent

router = APIRouter(prefix="/blogs", tags=["Blog"])

@router.get("/", response_model=List[dict])
async def list_blogs(
    limit: int = 10,
    db: DatabasePort = Depends(get_db)
):
    """
    Public endpoint: List recent blog posts.
    """
    return await db.list_blog_posts(limit=limit)

@router.get("/{slug}", response_model=dict)
async def get_blog(
    slug: str,
    db: DatabasePort = Depends(get_db)
):
    """
    Public endpoint: Get a single blog post by slug.
    """
    post = await db.get_blog_post(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_blog_post(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
    ai: AIPort = Depends(get_ai_service)
):
    """
    Admin only: Manually trigger AI blog generation.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    agent = BlogAgent(db, ai)
    post = await agent.generate_weekly_digest()
    
    if not post:
         raise HTTPException(status_code=500, detail="Failed to generate post (no data?)")
         
    return post

@router.post("/refresh-trends", status_code=status.HTTP_201_CREATED)
async def refresh_market_trends(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: DatabasePort = Depends(get_db),
    ai: AIPort = Depends(get_ai_service)
):
    """
    Admin only: Trigger 'Big 4 Campus Watch' generation using Real-Time News.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    agent = BlogAgent(db, ai)
    post = await agent.generate_weekly_digest()
    
    if not post:
         raise HTTPException(status_code=500, detail="Failed to generate post (no news found?)")
         
    return post
