"""SQLAlchemy ORM schema. Every tenant-owned table carries hospital_id and every query is scoped by it."""
import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    HOSPITAL_ADMIN = "hospital_admin"
    OPHTHALMOLOGIST = "ophthalmologist"
    TECHNICIAN = "technician"
    RECEPTIONIST = "receptionist"


class ScreeningStatus(str, enum.Enum):
    DRAFT = "draft"                      # created, awaiting images
    QUALITY_CHECKED = "quality_checked"  # images uploaded + quality assessed
    ANALYSED = "analysed"                # AI step executed (or recorded as unavailable)
    IN_REVIEW = "in_review"              # clinician has opened / saved a draft review
    RECAPTURE_REQUESTED = "recapture_requested"
    SIGNED = "signed"                    # clinician signed the review
    REPORTED = "reported"                # approved report generated


class Plan(Base):
    __tablename__ = "plans"
    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(255), default="")
    monthly_price_inr: Mapped[int] = mapped_column(Integer, default=0)
    annual_price_inr: Mapped[int] = mapped_column(Integer, default=0)
    max_screenings_per_month: Mapped[int] = mapped_column(Integer, default=0)  # 0 = unlimited
    max_users: Mapped[int] = mapped_column(Integer, default=0)
    max_branches: Mapped[int] = mapped_column(Integer, default=1)
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Hospital(Base):
    __tablename__ = "hospitals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(8), unique=True)  # used in patient IDs, e.g. NR-AEH-000123
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    state: Mapped[str] = mapped_column(String(100), default="")
    gstin: Mapped[str] = mapped_column(String(20), default="")
    # Branding
    brand_color: Mapped[str] = mapped_column(String(9), default="#0B1F3A")
    logo_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    report_header: Mapped[str] = mapped_column(String(300), default="")
    report_footer: Mapped[str] = mapped_column(String(500), default="")
    # Commercial
    plan_code: Mapped[str] = mapped_column(ForeignKey("plans.code"), default="STARTER")
    billing_cycle: Mapped[str] = mapped_column(String(10), default="monthly")
    licence_status: Mapped[str] = mapped_column(String(20), default="trial")  # trial|active|suspended|expired
    licence_key: Mapped[str] = mapped_column(String(64), default="")
    licence_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_days: Mapped[int] = mapped_column(Integer, default=365 * 7)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    plan: Mapped[Plan] = relationship()
    branches: Mapped[list["Branch"]] = relationship(back_populates="hospital", cascade="all, delete-orphan")


class Branch(Base):
    __tablename__ = "branches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospitals.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    hospital: Mapped[Hospital] = relationship(back_populates="branches")


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    hospital_id: Mapped[str | None] = mapped_column(ForeignKey("hospitals.id"), index=True, nullable=True)
    branch_id: Mapped[str | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(40), default="")
    medical_registration_no: Mapped[str] = mapped_column(String(60), default="")  # for ophthalmologists
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    hospital: Mapped[Hospital | None] = relationship()


class UserSession(Base):
    """Refresh-token sessions; revocable (logout, password change, admin force-logout)."""
    __tablename__ = "user_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)  # = refresh token jti
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(300), default="")


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (UniqueConstraint("hospital_id", "patient_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospitals.id"), index=True)
    branch_id: Mapped[str | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    patient_code: Mapped[str] = mapped_column(String(40), index=True)  # human-readable unique ID
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100), default="")
    date_of_birth: Mapped[date] = mapped_column(Date)
    sex: Mapped[str] = mapped_column(String(16), default="unspecified")
    phone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    emergency_contact: Mapped[str] = mapped_column(String(200), default="")
    abha_id: Mapped[str] = mapped_column(String(40), default="")  # Ayushman Bharat Health Account (optional)
    medical_history: Mapped[str] = mapped_column(Text, default="")
    has_diabetes: Mapped[bool] = mapped_column(Boolean, default=False)
    diabetes_type: Mapped[str] = mapped_column(String(20), default="")
    diabetes_since_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_hba1c: Mapped[float | None] = mapped_column(Float, nullable=True)
    has_hypertension: Mapped[bool] = mapped_column(Boolean, default=False)
    hypertension_since_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    medications: Mapped[str] = mapped_column(Text, default="")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)  # clearly-labelled demo/test patients
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    consents: Mapped[list["ConsentRecord"]] = relationship(back_populates="patient", cascade="all, delete-orphan",
                                                           order_by="ConsentRecord.recorded_at")
    screenings: Mapped[list["Screening"]] = relationship(back_populates="patient", order_by="Screening.created_at.desc()")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def age(self) -> int:
        today = date.today()
        d = self.date_of_birth
        return today.year - d.year - ((today.month, today.day) < (d.month, d.day))


class ConsentRecord(Base):
    __tablename__ = "consent_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospitals.id"), index=True)
    consent_type: Mapped[str] = mapped_column(String(40))  # screening | ai_analysis | data_storage | research
    granted: Mapped[bool] = mapped_column(Boolean)
    method: Mapped[str] = mapped_column(String(40), default="written")  # written | digital | verbal_witnessed
    language: Mapped[str] = mapped_column(String(30), default="English")
    notes: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    patient: Mapped[Patient] = relationship(back_populates="consents")


class Screening(Base):
    __tablename__ = "screenings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospitals.id"), index=True)
    branch_id: Mapped[str | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    screening_code: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(32), default=ScreeningStatus.DRAFT.value)
    camera_device: Mapped[str] = mapped_column(String(200), default="")
    dilated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    patient: Mapped[Patient] = relationship(back_populates="screenings")
    images: Mapped[list["RetinalImage"]] = relationship(back_populates="screening", order_by="RetinalImage.uploaded_at")
    ai_results: Mapped[list["AIResult"]] = relationship(back_populates="screening", order_by="AIResult.created_at")
    reviews: Mapped[list["ClinicalReview"]] = relationship(back_populates="screening", order_by="ClinicalReview.created_at")
    reports: Mapped[list["Report"]] = relationship(back_populates="screening", order_by="Report.generated_at")


class RetinalImage(Base):
    __tablename__ = "retinal_images"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    screening_id: Mapped[str] = mapped_column(ForeignKey("screenings.id"), index=True)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospitals.id"), index=True)
    eye: Mapped[str] = mapped_column(String(8))  # right | left
    storage_key: Mapped[str] = mapped_column(String(300))
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(60))
    file_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    image_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    quality: Mapped[dict] = mapped_column(JSON, default=dict)
    quality_verdict: Mapped[str] = mapped_column(String(32), default="pending")  # acceptable|recapture_required|inconclusive
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)  # False once replaced (kept for audit)
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    screening: Mapped[Screening] = relationship(back_populates="images")


class AIResult(Base):
    """Immutable record of what the model produced. Never edited by clinicians (their view lives in ClinicalReview)."""
    __tablename__ = "ai_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    screening_id: Mapped[str] = mapped_column(ForeignKey("screenings.id"), index=True)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospitals.id"), index=True)
    image_id: Mapped[str] = mapped_column(ForeignKey("retinal_images.id"))
    eye: Mapped[str] = mapped_column(String(8))
    module: Mapped[str] = mapped_column(String(40))  # diabetic_retinopathy, ...
    status: Mapped[str] = mapped_column(String(32))  # completed | model_unavailable | quality_rejected | error
    model_name: Mapped[str] = mapped_column(String(120), default="")
    model_version: Mapped[str] = mapped_column(String(60), default="")
    predicted_label: Mapped[str] = mapped_column(String(60), default="")
    predicted_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    probabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    normalized_entropy: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_uncertain: Mapped[bool] = mapped_column(Boolean, default=True)
    display_verdict: Mapped[str] = mapped_column(String(120))
    explanation: Mapped[str] = mapped_column(Text, default="")
    gradcam_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    inference_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    screening: Mapped[Screening] = relationship(back_populates="ai_results")


class ClinicalReview(Base):
    __tablename__ = "clinical_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    screening_id: Mapped[str] = mapped_column(ForeignKey("screenings.id"), index=True)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospitals.id"), index=True)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    # per eye: {"right": {"ai_decision": "accept|modify|reject|not_applicable", "final_grade": "...", "observations": "..."}}
    eye_findings: Mapped[dict] = mapped_column(JSON, default=dict)
    overall_impression: Mapped[str] = mapped_column(Text, default="")
    recommendations: Mapped[str] = mapped_column(Text, default="")
    referral_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    referral_urgency: Mapped[str] = mapped_column(String(20), default="")  # routine|soon|urgent
    referral_to: Mapped[str] = mapped_column(String(200), default="")
    follow_up_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recapture_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    recapture_reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | signed
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signature_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    screening: Mapped[Screening] = relationship(back_populates="reviews")
    reviewer: Mapped[User] = relationship()


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    report_number: Mapped[str] = mapped_column(String(60), unique=True)
    screening_id: Mapped[str] = mapped_column(ForeignKey("screenings.id"), index=True)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospitals.id"), index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    review_id: Mapped[str | None] = mapped_column(ForeignKey("clinical_reviews.id"), nullable=True)
    review_status: Mapped[str] = mapped_column(String(40))  # "CLINICIAN APPROVED" only when review signed
    storage_key: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64))
    generated_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    screening: Mapped[Screening] = relationship(back_populates="reports")


class AuditLog(Base):
    """Append-only, hash-chained audit trail (tamper-evident)."""
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hospital_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    user_email: Mapped[str] = mapped_column(String(200), default="")
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(60), default="")
    entity_id: Mapped[str] = mapped_column(String(60), default="")
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")


class DemoRequest(Base):
    __tablename__ = "demo_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    organisation: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(40), default="")
    role: Mapped[str] = mapped_column(String(100), default="")
    kind: Mapped[str] = mapped_column(String(20), default="demo")  # demo | contact
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    hospital_id: Mapped[str] = mapped_column(ForeignKey("hospitals.id"), index=True)
    invoice_number: Mapped[str] = mapped_column(String(40), unique=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    plan_code: Mapped[str] = mapped_column(String(32))
    subtotal_inr: Mapped[int] = mapped_column(Integer)
    gst_inr: Mapped[int] = mapped_column(Integer)
    total_inr: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="issued")  # issued | paid | void
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    payment_reference: Mapped[str] = mapped_column(String(100), default="")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
