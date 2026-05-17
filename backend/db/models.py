"""
NexusIQ — SQLAlchemy async ORM models.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float,
    ForeignKey, Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    manager  = "manager"
    employee = "employee"


class CourseStatus(str, enum.Enum):
    draft    = "draft"
    active   = "active"
    archived = "archived"


class DifficultyLevel(str, enum.Enum):
    beginner     = "beginner"
    intermediate = "intermediate"
    advanced     = "advanced"


class EmployeeCourseStatus(str, enum.Enum):
    assigned    = "assigned"
    in_progress = "in_progress"
    completed   = "completed"


# ── Models ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    first_name      = Column(String(100), nullable=False, default="")
    last_name       = Column(String(100), nullable=False, default="")
    hashed_password = Column(String(255), nullable=False)
    role            = Column(Enum(UserRole), nullable=False, default=UserRole.employee)
    is_active       = Column(Boolean, nullable=False, default=True)
    created_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    managed_courses    = relationship("Course", back_populates="manager",
                                      foreign_keys="Course.manager_id")
    course_enrollments = relationship("EmployeeCourse", back_populates="employee",
                                      foreign_keys="EmployeeCourse.employee_id")


class Course(Base):
    __tablename__ = "courses"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title       = Column(String(255), nullable=False)
    description = Column(Text, nullable=True, default="")
    mode        = Column(String(50), nullable=False, default="new_project")
    status      = Column(Enum(CourseStatus), nullable=False, default=CourseStatus.draft)
    manager_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tech_stack  = Column(JSON, nullable=True)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    manager     = relationship("User", back_populates="managed_courses",
                               foreign_keys=[manager_id])
    modules     = relationship("Module", back_populates="course",
                               cascade="all, delete-orphan", order_by="Module.order_index")
    enrollments = relationship("EmployeeCourse", back_populates="course")


class Module(Base):
    __tablename__ = "modules"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id           = Column(UUID(as_uuid=True),
                                 ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title               = Column(String(255), nullable=False)
    order_index         = Column(Integer, nullable=False, default=0)
    difficulty          = Column(Enum(DifficultyLevel), nullable=False,
                                 default=DifficultyLevel.intermediate)
    concepts            = Column(JSON, nullable=True)   # [{name, explanation, code_example}]
    learning_objectives = Column(JSON, nullable=True)   # [str]
    estimated_hours     = Column(Float, nullable=True, default=1.0)
    why_this_matters    = Column(Text, nullable=True)

    course   = relationship("Course", back_populates="modules")
    progress = relationship("ModuleProgress", back_populates="module",
                            cascade="all, delete-orphan")


class EmployeeCourse(Base):
    __tablename__ = "employee_courses"
    __table_args__ = (UniqueConstraint("employee_id", "course_id"),)

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id          = Column(UUID(as_uuid=True),
                                  ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id            = Column(UUID(as_uuid=True),
                                  ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    status               = Column(Enum(EmployeeCourseStatus), nullable=False,
                                  default=EmployeeCourseStatus.assigned)
    current_module_index = Column(Integer, nullable=False, default=0)
    consecutive_fails    = Column(Integer, nullable=False, default=0)
    session_id           = Column(String(255), nullable=True)
    created_at           = Column(DateTime(timezone=True),
                                  default=lambda: datetime.now(timezone.utc))
    updated_at           = Column(DateTime(timezone=True),
                                  default=lambda: datetime.now(timezone.utc),
                                  onupdate=lambda: datetime.now(timezone.utc))

    employee        = relationship("User", back_populates="course_enrollments",
                                   foreign_keys=[employee_id])
    course          = relationship("Course", back_populates="enrollments")
    module_progress = relationship("ModuleProgress", back_populates="enrollment",
                                   cascade="all, delete-orphan")


class ModuleProgress(Base):
    __tablename__ = "module_progress"
    __table_args__ = (UniqueConstraint("enrollment_id", "module_id"),)

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True),
                           ForeignKey("employee_courses.id", ondelete="CASCADE"), nullable=False)
    module_id     = Column(UUID(as_uuid=True),
                           ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    task_score      = Column(Float, nullable=True)
    interview_score = Column(Float, nullable=True)
    final_score     = Column(Float, nullable=True)
    passed          = Column(Boolean, nullable=False, default=False)
    attempts        = Column(Integer, nullable=False, default=0)
    completed_at    = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc))
    updated_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))

    enrollment = relationship("EmployeeCourse", back_populates="module_progress")
    module     = relationship("Module", back_populates="progress")
