from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    Enum,
    Text,
    Date,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()


class UserTypes(enum.Enum):
    super_admin = "super_admin"
    admin = "admin"
    receiver = "receiver"
    creator = "creator"


class BriefStatus(enum.Enum):
    waiting_for_approval = "waiting_for_approval"
    approved = "approved"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(50), nullable=False)
    user_firstname: Mapped[str] = mapped_column(String(30), nullable=False)
    user_lastname: Mapped[str] = mapped_column(String(30), nullable=False)
    user_email: Mapped[str] = mapped_column(String(70), unique=True, nullable=False)
    user_role: Mapped[UserTypes] = mapped_column(
        Enum(UserTypes), nullable=False, default=UserTypes.creator
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Relationship linking User to Brief
    briefs: Mapped[list["Brief"]] = relationship("Brief", back_populates="creator")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.user_role})>"


class Brief(Base):
    __tablename__ = "briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str] = mapped_column(String(255), nullable=False)
    study_type: Mapped[str] = mapped_column(String(255), nullable=False)
    comments: Mapped[str] = mapped_column(Text, nullable=True)
    previous_research: Mapped[str] = mapped_column(Text, nullable=True)
    market_objective: Mapped[str] = mapped_column(Text, nullable=False)
    research_objective: Mapped[str] = mapped_column(Text, nullable=False)
    research_tg: Mapped[str] = mapped_column(Text, nullable=True)
    research_design: Mapped[str] = mapped_column(Text, nullable=True)
    key_information_area: Mapped[str] = mapped_column(Text, nullable=False)
    deadline: Mapped[Date] = mapped_column(Date, nullable=False)
    additional_information: Mapped[str] = mapped_column(Text, nullable=True)
    city: Mapped[str] = mapped_column(String(50), nullable=True)
    stimulus_dispatch_date: Mapped[Date] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="waiting_for_approval")
    attachments: Mapped[str] = mapped_column(String(255), nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str] = mapped_column(String(255), nullable=True)
    rejection_reason: Mapped[str] = mapped_column(Text, nullable=True)
    rejection_date: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    budget: Mapped[float] = mapped_column(Float, nullable=True)
    total_cost: Mapped[float] = mapped_column(Float, nullable=True)

    # Foreign key to the User table
    brief_creator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    # Relationship linking Brief to its creator (User)
    creator: Mapped["User"] = relationship("User", back_populates="briefs")

    def __repr__(self):
        return f"<Brief(id={self.id}, market_objective={self.market_objective}, status={self.status})>"
