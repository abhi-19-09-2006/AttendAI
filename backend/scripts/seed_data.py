"""
Seed data script for development.
"""
import asyncio
from datetime import date, datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import (
    User,
    Student,
    Parent,
    Attendance,
    CallCampaign,
    Call,
    CallAttempt,
    AbsenceReport,
    FollowUp,
    UserRole,
    AttendanceStatus,
    CallStatus,
    CampaignStatus,
    AbsenceCategory,
    FollowUpType,
    FollowUpPriority,
    FollowUpStatus,
    ParentRelationship,
    ContactMethod,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_users(db: AsyncSession):
    """Seed users."""
    users = [
        User(
            email="admin@attendai.example.com",
            hashed_password=pwd_context.hash("admin123"),
            full_name="Admin User",
            role=UserRole.ADMIN,
            department="Administration",
            is_active=True,
        ),
        User(
            email="faculty@attendai.example.com",
            hashed_password=pwd_context.hash("faculty123"),
            full_name="Jane Faculty",
            role=UserRole.FACULTY,
            department="Mathematics",
            is_active=True,
        ),
        User(
            email="staff@attendai.example.com",
            hashed_password=pwd_context.hash("staff123"),
            full_name="John Staff",
            role=UserRole.STAFF,
            department="Office",
            is_active=True,
        ),
    ]
    db.add_all(users)
    await db.flush()
    return users


async def seed_students_and_parents(db: AsyncSession):
    """Seed students and parents."""
    students_data = [
        {
            "student_id": "STU001",
            "first_name": "Emma",
            "last_name": "Johnson",
            "date_of_birth": date(2010, 5, 15),
            "grade_level": 8,
            "department": "Middle School",
            "parents": [
                {
                    "relationship": ParentRelationship.MOTHER,
                    "first_name": "Sarah",
                    "last_name": "Johnson",
                    "primary_phone": "+1234567890",
                    "email": "sarah.johnson@email.com",
                    "is_primary_contact": True,
                }
            ],
        },
        {
            "student_id": "STU002",
            "first_name": "Liam",
            "last_name": "Williams",
            "date_of_birth": date(2011, 3, 22),
            "grade_level": 7,
            "department": "Middle School",
            "parents": [
                {
                    "relationship": ParentRelationship.FATHER,
                    "first_name": "Michael",
                    "last_name": "Williams",
                    "primary_phone": "+1234567891",
                    "email": "michael.williams@email.com",
                    "is_primary_contact": True,
                }
            ],
        },
        {
            "student_id": "STU003",
            "first_name": "Olivia",
            "last_name": "Brown",
            "date_of_birth": date(2009, 9, 10),
            "grade_level": 9,
            "department": "High School",
            "parents": [
                {
                    "relationship": ParentRelationship.MOTHER,
                    "first_name": "Jennifer",
                    "last_name": "Brown",
                    "primary_phone": "+1234567892",
                    "email": "jennifer.brown@email.com",
                    "is_primary_contact": True,
                },
                {
                    "relationship": ParentRelationship.FATHER,
                    "first_name": "Robert",
                    "last_name": "Brown",
                    "primary_phone": "+1234567893",
                    "secondary_phone": "+1234567894",
                    "email": "robert.brown@email.com",
                    "is_primary_contact": False,
                },
            ],
        },
        {
            "student_id": "STU004",
            "first_name": "Noah",
            "last_name": "Davis",
            "date_of_birth": date(2010, 11, 5),
            "grade_level": 8,
            "department": "Middle School",
            "parents": [
                {
                    "relationship": ParentRelationship.GUARDIAN,
                    "first_name": "Margaret",
                    "last_name": "Davis",
                    "primary_phone": "+1234567895",
                    "email": "margaret.davis@email.com",
                    "is_primary_contact": True,
                }
            ],
        },
        {
            "student_id": "STU005",
            "first_name": "Sophia",
            "last_name": "Martinez",
            "date_of_birth": date(2011, 7, 18),
            "grade_level": 7,
            "department": "Middle School",
            "parents": [
                {
                    "relationship": ParentRelationship.MOTHER,
                    "first_name": "Maria",
                    "last_name": "Martinez",
                    "primary_phone": "+1234567896",
                    "email": "maria.martinez@email.com",
                    "preferred_language": "es",
                    "is_primary_contact": True,
                }
            ],
        },
    ]

    students = []
    parents_list = []

    for student_data in students_data:
        parents_data = student_data.pop("parents")
        student = Student(**student_data, is_active=True)
        db.add(student)
        await db.flush()

        for parent_data in parents_data:
            parent = Parent(**parent_data, student_id=student.id)
            db.add(parent)
            parents_list.append(parent)

        students.append(student)

    await db.flush()
    return students, parents_list


async def seed_attendance(db: AsyncSession, students, users):
    """Seed attendance records."""
    faculty_user = next(u for u in users if u.role == UserRole.FACULTY)
    today = date.today()
    attendance_records = []

    # Create attendance for past 5 days
    for days_ago in range(5):
        attendance_date = today - timedelta(days=days_ago)

        for idx, student in enumerate(students):
            # Make some students absent on specific days
            if days_ago == 0 and idx in [0, 2]:  # Today: Emma and Olivia absent
                status = AttendanceStatus.ABSENT
            elif days_ago == 1 and idx == 1:  # Yesterday: Liam absent
                status = AttendanceStatus.ABSENT
            elif days_ago == 2 and idx == 4:  # 2 days ago: Sophia late
                status = AttendanceStatus.LATE
            else:
                status = AttendanceStatus.PRESENT

            attendance = Attendance(
                student_id=student.id,
                date=attendance_date,
                status=status,
                recorded_by=faculty_user.id,
                notes=f"Attendance for {attendance_date}" if status == AttendanceStatus.ABSENT else None,
            )
            db.add(attendance)
            attendance_records.append(attendance)

    await db.flush()
    return attendance_records


async def seed_campaigns_and_calls(db: AsyncSession, students, parents_list, attendance_records, users):
    """Seed call campaigns and calls."""
    admin_user = next(u for u in users if u.role == UserRole.ADMIN)

    # Create a campaign
    campaign = CallCampaign(
        name="Daily Absence Calls",
        description="Automated calls for today's absences",
        status=CampaignStatus.ACTIVE,
        created_by=admin_user.id,
        scheduled_start=datetime.utcnow(),
    )
    db.add(campaign)
    await db.flush()

    # Create calls for absent students
    calls = []
    today = date.today()
    absent_today = [att for att in attendance_records if att.status == AttendanceStatus.ABSENT and att.date == today]

    for attendance in absent_today[:2]:  # Only first 2 absences for demo
        student = next(s for s in students if s.id == attendance.student_id)
        primary_parent = next((p for p in parents_list if p.student_id == student.id and p.is_primary_contact), None)

        if not primary_parent:
            primary_parent = next(p for p in parents_list if p.student_id == student.id)

        call = Call(
            campaign_id=campaign.id,
            student_id=student.id,
            parent_id=primary_parent.id,
            attendance_id=attendance.id,
            status=CallStatus.COMPLETED if calls else CallStatus.PENDING,
            phone_number_called=primary_parent.primary_phone,
            scheduled_time=datetime.utcnow(),
            initiated_at=datetime.utcnow() - timedelta(minutes=10) if calls else None,
            answered_at=datetime.utcnow() - timedelta(minutes=9) if calls else None,
            ended_at=datetime.utcnow() - timedelta(minutes=6) if calls else None,
            duration_seconds=180 if calls else None,
            retry_count=0,
        )
        db.add(call)
        calls.append(call)

    await db.flush()
    return campaign, calls


async def seed_absence_reports(db: AsyncSession, calls, students, attendance_records):
    """Seed absence reports."""
    reports = []

    # Create report for first completed call
    if calls and calls[0].status == CallStatus.COMPLETED:
        call = calls[0]
        student = next(s for s in students if s.id == call.student_id)

        report = AbsenceReport(
            call_id=call.id,
            student_id=student.id,
            attendance_id=call.attendance_id,
            reason="Student has a fever and is not feeling well",
            category=AbsenceCategory.MEDICAL,
            duration="1-2 days",
            expected_return_date=date.today() + timedelta(days=2),
            parent_confirmed=True,
            follow_up_required=False,
            confidence_score=0.95,
            transcript="[Automated transcript: Parent confirmed student has fever. Expected return in 1-2 days.]",
            raw_extraction={
                "reason": "fever",
                "symptoms": ["fever", "not feeling well"],
                "confirmed_by_parent": True,
            },
        )
        db.add(report)
        reports.append(report)

    await db.flush()
    return reports


async def seed_followups(db: AsyncSession, students, calls):
    """Seed follow-up tasks."""
    followups = []

    # Create a follow-up for the pending call
    if len(calls) > 1 and calls[1].status == CallStatus.PENDING:
        followup = FollowUp(
            call_id=calls[1].id,
            student_id=calls[1].student_id,
            type=FollowUpType.CALLBACK_REQUESTED,
            priority=FollowUpPriority.HIGH,
            status=FollowUpStatus.PENDING,
            due_date=date.today(),
            description="Parent did not answer. Callback requested.",
        )
        db.add(followup)
        followups.append(followup)

    await db.flush()
    return followups


async def main():
    """Main seed function."""
    print("🌱 Starting database seeding...")

    async with AsyncSessionLocal() as db:
        try:
            # Seed in order
            print("Creating users...")
            users = await seed_users(db)

            print("Creating students and parents...")
            students, parents = await seed_students_and_parents(db)

            print("Creating attendance records...")
            attendance_records = await seed_attendance(db, students, users)

            print("Creating campaigns and calls...")
            campaign, calls = await seed_campaigns_and_calls(db, students, parents, attendance_records, users)

            print("Creating absence reports...")
            reports = await seed_absence_reports(db, calls, students, attendance_records)

            print("Creating follow-ups...")
            followups = await seed_followups(db, students, calls)

            await db.commit()

            print("\n✅ Database seeding completed successfully!")
            print("\n📊 Summary:")
            print(f"   Users: {len(users)}")
            print(f"   Students: {len(students)}")
            print(f"   Parents: {len(parents)}")
            print(f"   Attendance records: {len(attendance_records)}")
            print(f"   Campaigns: 1")
            print(f"   Calls: {len(calls)}")
            print(f"   Absence reports: {len(reports)}")
            print(f"   Follow-ups: {len(followups)}")
            print("\n👤 Test Users:")
            print("   Admin:   admin@attendai.example.com / admin123")
            print("   Faculty: faculty@attendai.example.com / faculty123")
            print("   Staff:   staff@attendai.example.com / staff123")

        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error seeding database: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
