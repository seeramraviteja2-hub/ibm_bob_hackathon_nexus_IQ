"""
NexusIQ — Demo cache.
Pre-baked high-fidelity responses used when DEMO_MODE=true.
Zero LLM calls, zero rate-limit risk during live demos.
"""
import os

DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"

DEMO_SKILL_MANIFEST = {
    "project_name": "FastAPI Microservice",
    "tech_stack": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"],
    "core_concepts": [
        "Async Python with asyncio",
        "FastAPI dependency injection",
        "SQLAlchemy async ORM",
        "Redis pub/sub",
        "JWT authentication",
    ],
    "learning_objectives": [
        "Build production-ready async REST APIs",
        "Implement secure JWT auth flows",
        "Design scalable database schemas",
        "Use Redis for caching and real-time messaging",
    ],
    "difficulty_level": "intermediate",
    "estimated_hours": 12,
}

DEMO_COURSE_PLAN = {
    "title": "FastAPI Microservice Development",
    "modules": [
        {
            "index": 0,
            "title": "Async Python Fundamentals",
            "concepts": ["asyncio event loop", "async/await syntax", "coroutines vs threads"],
            "code_examples": [
                {"code": "async def fetch_data():\n    await asyncio.sleep(1)\n    return {'data': 'value'}",
                 "explanation": "Basic async function pattern"}
            ],
            "learning_goals": [
                "Understand event loop execution",
                "Write non-blocking I/O code",
                "Avoid common async pitfalls",
            ],
            "estimated_minutes": 120,
        },
        {
            "index": 1,
            "title": "FastAPI Deep Dive",
            "concepts": ["path operations", "dependency injection", "Pydantic models", "middleware"],
            "code_examples": [
                {"code": "@app.get('/items/{item_id}')\nasync def read_item(item_id: int, db: Session = Depends(get_db)):\n    return db.get(Item, item_id)",
                 "explanation": "Route with dependency injection"}
            ],
            "learning_goals": [
                "Design RESTful API routes",
                "Use FastAPI DI system",
                "Validate requests with Pydantic",
            ],
            "estimated_minutes": 150,
        },
        {
            "index": 2,
            "title": "Database & Auth",
            "concepts": ["SQLAlchemy async", "Alembic migrations", "JWT tokens", "password hashing"],
            "code_examples": [
                {"code": "async with async_session() as db:\n    result = await db.execute(select(User).where(User.email == email))\n    user = result.scalar_one_or_none()",
                 "explanation": "Async SQLAlchemy query pattern"}
            ],
            "learning_goals": [
                "Implement async DB operations",
                "Create secure auth endpoints",
                "Manage DB migrations",
            ],
            "estimated_minutes": 180,
        },
    ],
}

DEMO_TEACHING_RESPONSE = (
    "Great question! Let me explain this concept step by step. "
    "In async Python, the event loop manages coroutines — lightweight functions "
    "that can pause and resume without blocking the thread. "
    "Unlike threads, coroutines are cooperative: they yield control explicitly "
    "using `await`. This makes them ideal for I/O-heavy work like database calls "
    "and HTTP requests. Do you want me to show a concrete example comparing "
    "sync vs async database queries?"
)

DEMO_TASK = {
    "task_title": "Build a User Authentication Endpoint",
    "description": (
        "Implement a complete JWT authentication flow in FastAPI. "
        "Create POST /register and POST /login endpoints that securely "
        "store and verify user credentials."
    ),
    "requirements": [
        "Hash passwords with bcrypt before storing",
        "Return a signed JWT on successful login",
        "Protect at least one route with the JWT dependency",
        "Handle duplicate email registration gracefully",
    ],
    "evaluation_criteria": [
        "Passwords never stored in plain text",
        "JWT contains user_id and role claims",
        "Protected route returns 401 without valid token",
        "Async SQLAlchemy used for all DB operations",
    ],
    "hints": [
        "Use passlib.context.CryptContext for bcrypt",
        "python-jose handles JWT encode/decode",
        "FastAPI's HTTPBearer extracts the token from the Authorization header",
    ],
}

DEMO_INTERVIEW_QUESTIONS = [
    "What is the difference between `async def` and a regular `def` in Python?",
    "Why is `await` necessary when calling async functions?",
    "How does FastAPI's dependency injection system work?",
    "What problem does JWT solve compared to session-based auth?",
    "Explain how bcrypt's work factor affects security vs performance.",
    "What does `expire_on_commit=False` do in SQLAlchemy's session factory?",
    "How would you handle a database connection pool exhaustion?",
    "What is the purpose of Pydantic's `model_config = {'from_attributes': True}`?",
    "How do you prevent SQL injection when using SQLAlchemy ORM?",
]
