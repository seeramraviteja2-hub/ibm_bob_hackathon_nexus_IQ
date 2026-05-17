"""
NexusIQ — Pydantic schemas for Course and Module API endpoints.
"""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ModuleCreate(BaseModel):
    title: str
    order_index: int = 0
    difficulty: str = "intermediate"
    concepts: list[dict] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)
    estimated_hours: float = 1.0
    why_this_matters: Optional[str] = None


class ModuleResponse(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    order_index: int
    difficulty: str
    concepts: list[dict]
    learning_objectives: list[str]
    estimated_hours: float
    why_this_matters: Optional[str]

    model_config = {"from_attributes": True, "use_enum_values": True}


class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    mode: str = "new_project"           # "new_project" | "legacy_codebase"
    tech_stack: Optional[dict] = None   # {"difficulty": "intermediate", ...}


class CourseResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    mode: str
    status: str
    manager_id: UUID
    total_modules: int = 0

    model_config = {"from_attributes": True, "use_enum_values": True}

    @classmethod
    def from_orm_with_count(cls, course) -> "CourseResponse":
        return cls(
            id=course.id,
            title=course.title,
            description=course.description,
            mode=course.mode,
            status=course.status.value if hasattr(course.status, "value") else course.status,
            manager_id=course.manager_id,
            total_modules=len(course.modules) if course.modules else 0,
        )
