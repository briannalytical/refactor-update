import sys
import psycopg2
from datetime import date, datetime
from typing import Optional, Tuple, List, Dict, Any
from psycopg2.extensions import cursor as PgCursor, connection as PgConnection



### DATABASE SCHEMA INITIALIZATION ###
### ============================== ###
def initialize_database(cursor, conn):
    """Initialize database schema if it doesn't exist."""

    # Create custom enum types if they don't exist
    cursor.execute("""
        DO $$ BEGIN
            CREATE TYPE application_status_enum AS ENUM (
                'applied',
                'interviewing_first_scheduled',
                'interviewing_first_completed',
                'interviewing_first_followed_up',
                'interviewing_second_scheduled',
                'interviewing_second_completed',
                'interviewing_second_followed_up',
                'interviewing_final_scheduled',
                'interviewing_final_completed',
                'interviewing_final_followed_up',
                'offer_received',
                'rejected'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    cursor.execute("""
        DO $$ BEGIN
            CREATE TYPE next_action_enum AS ENUM (
                'check_application_status',
                'follow_up_with_contact',
                'send_follow_up_email',
                'prepare_for_interview',
                'send_thank_you_email',
                'prepare_for_second_interview',
                'send_thank_you_email_second_interview',
                'prepare_for_final_interview',
                'send_thank_you_email_final_interview'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create the main table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS application_tracking (
            id SERIAL PRIMARY KEY,
            job_title VARCHAR(255),
            company VARCHAR(255),
            application_status application_status_enum DEFAULT 'applied',
            date_applied DATE DEFAULT CURRENT_DATE,
            application_software VARCHAR(100),
            job_notes TEXT,
            follow_up_contact_name VARCHAR(255),
            follow_up_contact_details VARCHAR(255),
            next_action next_action_enum,
            check_application_status TIMESTAMP,
            next_follow_up_date TIMESTAMP,
            interview_date DATE,
            interview_time TIME,
            interviewer_name VARCHAR(255),
            interview_prep_notes TEXT,
            second_interview_date DATE,
            final_interview_date DATE,
            is_priority BOOLEAN DEFAULT FALSE,
            source_type VARCHAR(20) DEFAULT 'application',
            recruiter_name VARCHAR(255),
            recruiting_company VARCHAR(255),
            initial_call_date DATE,
            initial_call_time TIME,
            resume_sent BOOLEAN DEFAULT FALSE,
            resume_sent_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create function to automatically set check_application_status date
    cursor.execute("""
        CREATE OR REPLACE FUNCTION set_check_application_status()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.application_status = 'applied' THEN
                NEW.check_application_status := NEW.date_applied + INTERVAL '2 weeks';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger if it doesn't exist
    cursor.execute("""
        DO $$ BEGIN
            CREATE TRIGGER trigger_set_check_application_status
                BEFORE INSERT ON application_tracking
                FOR EACH ROW
                EXECUTE FUNCTION set_check_application_status();
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create function to update updated_at timestamp
    cursor.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger for updated_at
    cursor.execute("""
        DO $$ BEGIN
            CREATE TRIGGER trigger_update_updated_at
                BEFORE UPDATE ON application_tracking
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    conn.commit()
    print("✅ Database schema initialized successfully!")



# CONFIGURATION & CONSTANTS #
# ========================= #
DB_CONFIG = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'your_password_here',
    'host': 'localhost',
    'port': '5432'
}

AUTO_STATUS_MAP = {
    'check_application_status': 'interviewing_first_scheduled',
    'follow_up_with_contact': 'interviewing_first_scheduled',
    'send_follow_up_email': 'interviewing_first_followed_up',
    'prepare_for_interview': 'interviewing_first_completed',
    'send_thank_you_email': 'interviewing_first_followed_up',
    'prepare_for_second_interview': 'interviewing_second_completed',
    'send_thank_you_email_second_interview': 'interviewing_second_followed_up',
    'prepare_for_final_interview': 'interviewing_final_completed',
    'send_thank_you_email_final_interview': 'interviewing_final_followed_up'
}

STATUS_DISPLAY_MAP = {
    'applied': 'Applied',
    'interviewing_first_scheduled': 'First Interview Scheduled',
    'interviewing_first_completed': 'First Interview Completed',
    'interviewing_first_followed_up': 'First Interview Completed - Follow-up Sent',
    'interviewing_second_scheduled': 'Second Interview Scheduled',
    'interviewing_second_completed': 'Second Interview Completed',
    'interviewing_second_followed_up': 'Second Interview Completed - Follow-up Sent',
    'interviewing_final_scheduled': 'Final Interview Scheduled',
    'interviewing_final_completed': 'Final Interview Completed',
    'interviewing_final_followed_up': 'Final Interview Completed - Follow-up Sent',
    'offer_received': 'Offer Received',
    'rejected': 'Rejected'
}

STATUS_OPTIONS = {
    "Applied": "applied",
    "First Interview Scheduled": "interviewing_first_scheduled",
    "First Interview Completed": "interviewing_first_completed",
    "Post First Interview Follow-Up Sent": "interviewing_first_followed_up",
    "Second Interview Scheduled": "interviewing_second_scheduled",
    "Second Interview Completed": "interviewing_second_completed",
    "Post Second Interview Follow-Up Sent": "interviewing_second_followed_up",
    "Final Interview Scheduled": "interviewing_final_scheduled",
    "Final Interview Completed": "interviewing_final_completed",
    "Post Final Interview Follow-Up Sent": "interviewing_final_followed_up",
    "Offer Received": "offer_received",
    "Rejected": "rejected"
}


# DATABASE CONNECTION #
# =================== #
class DatabaseConnection:
    """Context manager for database connections."""

    def __init__(self, config: Dict[str, str], initialize: bool = False):
        self.config = config
        self.initialize = initialize
        self.conn: Optional[PgConnection] = None
        self.cursor: Optional[PgCursor] = None

    def __enter__(self) -> Tuple[PgConnection, PgCursor]:
        try:
            self.conn = psycopg2.connect(**self.config)
            self.cursor = self.conn.cursor()

            if self.initialize:
                initialize_database(self.cursor, self.conn)

            return self.conn, self.cursor
        except psycopg2.Error as e:
            print(f"\n❌ Database connection failed: {e}")
            sys.exit(1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()



# DISPLAY UTILITIES #
# ================= #
class Display:
    """Handles all user-facing display messages."""

    @staticmethod
    def intro():
        print("\n Hello! Welcome to Refactor, your job application tracker! I hope you will find this tool useful! 🥰")
        print("It's tough out there, but tracking your applications doesn't have to be!")
        print(
            "You can use this tool to track applications, remind you when to follow up, and schedule your interviews!")
        print("You can press X + enter at any point to return to the main menu!")

    @staticmethod
    def main_menu():
        print("\nWhat would you like to do? Enter your choice below:")
        print("\nVIEW: View all applications")
        print("TASKS: View today's tasks")
        print("ENTER: Track a new job application")
        print("UPDATE: Update an existing application")
        print("TIPS: Some helpful tips to keep in mind as you apply")
        print("BYE: End your session")

    @staticmethod
    def invalid_number():
        print("\n😭 Invalid number selection. Please select from available options.")

    @staticmethod
    def invalid_letter():
        print("\n😭 This character does not exist in this context. Try choosing from the available options.")

    @staticmethod
    def invalid_yes_no():
        print("\n😭 Please select Y or N.")

    @staticmethod
    def exit_to_menu():
        print("\n🔙 Returning to main menu.")

    @staticmethod
    def deletion_cancelled():
        print("\n❌ Deletion has been cancelled.")

    @staticmethod
    def format_status(status: str) -> str:
        return STATUS_DISPLAY_MAP.get(status, status.replace('_', ' ').title())

    @staticmethod
    def format_priority(is_priority: bool) -> str:
        return "‼️ Priority" if is_priority else ""

    @staticmethod
    def format_datetime(val: Any) -> str:
        if isinstance(val, date):
            return val.strftime("%B %d, %Y")
        elif isinstance(val, datetime):
            return val.strftime("%I:%M %p")
        return str(val)


# INPUT UTILITIES #
# =============== #
class Input:
    """Handles user input with validation."""

    @staticmethod
    def get_yes_no_exit(prompt: str) -> str:
        """Get Y/N/X input with validation."""
        while True:
            response = input(prompt).strip().upper()
            if response in ['Y', 'N', 'X']:
                return response
            Display.invalid_yes_no()

    @staticmethod
    def get_yes_no(prompt: str) -> str:
        """Get Y/N input with validation."""
        while True:
            response = input(prompt).strip().upper()
            if response in ['Y', 'N']:
                return response
            Display.invalid_yes_no()

    @staticmethod
    def get_number(prompt: str, min_val: int, max_val: int, allow_exit: bool = True) -> Optional[int]:
        """Get numeric input within a range."""
        while True:
            response = input(prompt).strip().upper()
            if allow_exit and response == 'X':
                return None
            try:
                num = int(response)
                if min_val <= num <= max_val:
                    return num
                Display.invalid_number()
            except ValueError:
                Display.invalid_number()

    @staticmethod
    def get_string(prompt: str, allow_empty: bool = True) -> Optional[str]:
        """Get string input."""
        value = input(prompt).strip()
        if value.upper() == 'X':
            return None
        if not allow_empty and not value:
            return Input.get_string(prompt, allow_empty)
        return value if value else None



# DATABASE OPERATIONS #
# =================== #
class ApplicationDB:
    """Handles all database operations for applications."""

    def __init__(self, cursor: PgCursor, conn: PgConnection):
        self.cursor = cursor
        self.conn = conn

    def update_status(self, app_id: int, next_action: Optional[str]) -> Optional[str]:
        """Auto-update application status based on next action."""
        if next_action and next_action in AUTO_STATUS_MAP:
            new_status = AUTO_STATUS_MAP[next_action]
            self.cursor.execute(
                "UPDATE application_tracking SET application_status = %s WHERE id = %s",
                (new_status, app_id)
            )
            self.conn.commit()
            return new_status
        return None

    def manual_status_update(self, app_id: int) -> Optional[str]:
        """Prompt user to manually update application status."""
        print("\n📌 Select new status:")
        labels = list(STATUS_OPTIONS.keys())
        for i, label in enumerate(labels, 1):
            print(f"{i}. {label}")

        selection = Input.get_number("Enter the number (or X to exit): ", 1, len(labels))
        if selection is None:
            return None

        new_status = STATUS_OPTIONS[labels[selection - 1]]
        self.cursor.execute(
            "UPDATE application_tracking SET application_status = %s WHERE id = %s",
            (new_status, app_id)
        )
        self.conn.commit()
        return new_status

    def update_contact_info(self, app_id: int, contact_name: str, contact_details: str):
        """Update contact information for an application."""
        self.cursor.execute(
            """UPDATE application_tracking 
               SET follow_up_contact_name = %s, follow_up_contact_details = %s 
               WHERE id = %s""",
            (contact_name or None, contact_details or None, app_id)
        )
        self.conn.commit()

    def get_all_applications(self, active_only: bool = False) -> List[Tuple]:
        """Retrieve all applications."""
        query = """
            SELECT company, job_title, id, application_status, date_applied, 
                   follow_up_contact_name, follow_up_contact_details, is_priority 
            FROM application_tracking
        """
        if active_only:
            query += " WHERE application_status != 'rejected'"
        query += " ORDER BY is_priority DESC, company ASC, date_applied ASC"

        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_application_by_id(self, app_id: int) -> Optional[Tuple]:
        """Get a specific application by ID."""
        self.cursor.execute(
            """SELECT * FROM application_tracking WHERE id = %s""",
            (app_id,)
        )
        return self.cursor.fetchone()

    def get_backlog_tasks(self, today: date) -> List[Tuple]:
        """Get overdue tasks."""
        query = """
            SELECT id, job_title, company, next_action, check_application_status, 
                   follow_up_contact_name, follow_up_contact_details, application_status, 
                   next_follow_up_date, interview_date, interview_time, 
                   second_interview_date, final_interview_date, is_priority
            FROM application_tracking
            WHERE (check_application_status::DATE < %s AND check_application_status IS NOT NULL)
               OR (next_follow_up_date::DATE < %s AND next_follow_up_date IS NOT NULL)
               OR (interview_date::DATE < %s AND interview_date IS NOT NULL)
               OR (second_interview_date::DATE < %s AND second_interview_date IS NOT NULL)
               OR (final_interview_date::DATE < %s AND final_interview_date IS NOT NULL)
            ORDER BY is_priority DESC, check_application_status ASC
        """
        self.cursor.execute(query, (today, today, today, today, today))
        return self.cursor.fetchall()

    def get_daily_tasks(self, today: date) -> List[Tuple]:
        """Get tasks due today."""
        query = """
            SELECT id, job_title, company, next_action, check_application_status, 
                   follow_up_contact_name, follow_up_contact_details, application_status, 
                   next_follow_up_date, interview_date, interview_time, 
                   second_interview_date, final_interview_date, is_priority
            FROM application_tracking
            WHERE check_application_status::DATE = %s
               OR next_follow_up_date::DATE = %s
               OR interview_date::DATE = %s
               OR second_interview_date::DATE = %s
               OR final_interview_date::DATE = %s
            ORDER BY is_priority DESC, job_title
        """
        self.cursor.execute(query, (today, today, today, today, today))
        return self.cursor.fetchall()

    def add_application(self, job_title: str, company: str, software: Optional[str],
                        notes: Optional[str], contact_name: Optional[str],
                        contact_details: Optional[str], is_priority: bool):
        """Add a new job application."""
        self.cursor.execute(
            """INSERT INTO application_tracking 
               (job_title, company, application_software, job_notes,
                follow_up_contact_name, follow_up_contact_details, is_priority)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (job_title, company, software, notes, contact_name, contact_details, is_priority)
        )
        self.conn.commit()

    def delete_application(self, app_id: int):
        """Delete an application."""
        self.cursor.execute("DELETE FROM application_tracking WHERE id = %s", (app_id,))
        self.conn.commit()

    def update_interview(self, app_id: int, interview_date: str, interview_time: Optional[str],
                         interviewer_name: str, prep_notes: Optional[str]):
        """Update interview details."""
        self.cursor.execute(
            """UPDATE application_tracking 
               SET interview_date = %s, interview_time = %s, 
                   interviewer_name = %s, interview_prep_notes = %s
               WHERE id = %s""",
            (interview_date, interview_time, interviewer_name, prep_notes, app_id)
        )
        self.conn.commit()

    def update_notes(self, app_id: int, new_notes: str, append: bool = True):
        """Update or append notes."""
        if append:
            self.cursor.execute("SELECT job_notes FROM application_tracking WHERE id = %s", (app_id,))
            result = self.cursor.fetchone()
            current_notes = result[0] if result and result[0] else ""
            updated_notes = f"{current_notes}; {new_notes}" if current_notes else new_notes
        else:
            updated_notes = new_notes

        self.cursor.execute(
            "UPDATE application_tracking SET job_notes = %s WHERE id = %s",
            (updated_notes, app_id)
        )
        self.conn.commit()

    def update_priority(self, app_id: int, is_priority: bool):
        """Update priority status."""
        self.cursor.execute(
            "UPDATE application_tracking SET is_priority = %s WHERE id = %s",
            (is_priority, app_id)
        )
        self.conn.commit()



# BUSINESS LOGIC #
# ============== #
class ContactManager:
    """Handles contact information prompts and updates."""

    @staticmethod
    def prompt_for_contact_info(db: ApplicationDB, app_id: int,
                                contact_name: Optional[str],
                                contact_details: Optional[str]) -> bool:
        """Prompt user to add contact info if missing. Returns False if user exits."""
        if not contact_name and not contact_details:
            print("\n⚠️  No contact information found for this application.")
            print("💡 Tip: Finding a recruiter or hiring manager increases your chances of getting an interview!")
            print("  You will need this information to complete the task.")

            response = Input.get_yes_no_exit("\nWould you like to add contact information now? (Y/N/X): ")
            if response == 'X':
                return False

            if response == 'Y':
                contact_name = Input.get_string("Contact name: ")
                contact_details = Input.get_string("Contact email/phone/LinkedIn URL: ")
                db.update_contact_info(app_id, contact_name or "", contact_details or "")
                print("\n✅ Contact information added!")
        else:
            if contact_name:
                print(f"   → Contact: {contact_name}")
            if contact_details:
                print(f"   → Contact Info: {contact_details}")
        return True


class TaskProcessor:
    """Processes task completion and status updates."""

    def __init__(self, db: ApplicationDB):
        self.db = db

    def process_task_completion(self, task: Tuple, today: date) -> bool:
        """Process a single task. Returns False if user exits."""
        (app_id, job_title, company, next_action, check_date, contact_name,
         contact_details, current_status, follow_up_date, interview_date,
         interview_time, second_interview_date, final_interview_date, is_priority) = task

        # Display task details
        priority_indicator = " ‼️" if is_priority else ""
        print(f"\n📌 {job_title} @ {company}{priority_indicator}")
        print(f"   → Current Status: {Display.format_status(current_status)}")
        if next_action:
            print(f"   → Task: {next_action.replace('_', ' ').title()}")

        # Check contact info
        if not ContactManager.prompt_for_contact_info(self.db, app_id, contact_name, contact_details):
            return False

        # Show overdue dates
        self._display_overdue_dates(check_date, follow_up_date, interview_date,
                                    second_interview_date, final_interview_date, today)

        # Mark as completed
        response = Input.get_yes_no_exit("✅ Mark this task as completed? (Y/N/X): ")
        if response == 'X':
            return False

        if response == 'Y':
            new_status = self.db.update_status(app_id, next_action)
            if new_status:
                print(f"\n✅ Status auto-updated to: {Display.format_status(new_status)}\n")
            else:
                print("\n✅ Task marked as completed\n")

        # Manual status update option
        response = Input.get_yes_no_exit("\n✏️ Would you like to manually update the application status? (Y/N/X): ")
        if response == 'X':
            return False

        if response == 'Y':
            new_status = self.db.manual_status_update(app_id)
            if new_status:
                print(f"\n✅ Status manually updated to: {Display.format_status(new_status)}\n")
            else:
                print("\n⏭️ Skipped status update.\n")
        else:
            print("\n⏭️ Skipped status update.\n")

        return True

    @staticmethod
    def _display_overdue_dates(check_date, follow_up_date, interview_date,
                               second_interview_date, final_interview_date, today):
        """Display overdue dates for a task."""
        overdue_dates = []
        if check_date and check_date.date() < today:
            overdue_dates.append(f"Check status: {check_date.strftime('%B %d, %Y')}")
        if follow_up_date and follow_up_date.date() < today:
            overdue_dates.append(f"Follow up: {follow_up_date.strftime('%B %d, %Y')}")
        if interview_date and interview_date.date() < today:
            overdue_dates.append(f"Interview: {interview_date.strftime('%B %d, %Y')}")
        if second_interview_date and second_interview_date.date() < today:
            overdue_dates.append(f"2nd Interview: {second_interview_date.strftime('%B %d, %Y')}")
        if final_interview_date and final_interview_date.date() < today:
            overdue_dates.append(f"Final Interview: {final_interview_date.strftime('%B %d, %Y')}")

        if overdue_dates:
            print(f"   → Overdue: {', '.join(overdue_dates)}")
        print()



# MENU HANDLERS #
# ============= #
def _display_backlog_task(task: Tuple, today: date):
    """Display a single backlog task."""
    (app_id, job_title, company, next_action, check_date, _, _, current_status,
     follow_up_date, interview_date, _, second_interview_date,
     final_interview_date, is_priority) = task

    priority_indicator = " ‼️" if is_priority else ""
    print(f"📌 {job_title} @ {company} ({app_id}){priority_indicator}")
    if next_action:
        print(f"   → Task: {next_action.replace('_', ' ').title()}")

    TaskProcessor._display_overdue_dates(check_date, follow_up_date, interview_date,
                                         second_interview_date, final_interview_date, today)


class MenuHandler:
    """Handles all menu operations."""


    def __init__(self, db: ApplicationDB):
        self.db = db
        self.task_processor = TaskProcessor(db)


    def handle_view(self):
        """Handle VIEW menu option."""
        active_only = Input.get_yes_no_exit("\nDo you want to see only active applications? (Y/N) Press X to exit: ")
        if active_only == 'X':
            Display.exit_to_menu()
            return

        applications = self.db.get_all_applications(active_only == 'Y')

        if not applications:
            print("\n😶 No applications found.")
            return

        print("\n📄 Applications")
        print("=" * 60)

        for app in applications:
            company, job_title, app_id, status, date_applied, _, _, is_priority = app
            priority_indicator = "‼️ " if is_priority else ""
            print(f"{priority_indicator}{company}: {job_title} ({app_id})")
            print(f"   Status: {Display.format_status(status)}")
            print(f"   Date Applied: {Display.format_datetime(date_applied)}")
            print("=" * 60)

        # View details
        while True:
            app_id = Input.get_number("\nEnter application ID to view details, or press X to exit: ",
                                      1, 999999)
            if app_id is None:
                Display.exit_to_menu()
                return

            # Find and display application
            selected = next((app for app in applications if app[2] == app_id), None)
            if selected:
                self._display_application_details(app_id)
            else:
                Display.invalid_number()


    def _display_application_details(self, app_id: int):
        """Display detailed information for a single application."""
        app = self.db.get_application_by_id(app_id)
        if not app:
            print("\n❌ Application not found.")
            return

        print(f"\n📄 Application Details: {app_id}")
        print("=" * 60)

        # This would need column names from cursor.description
        # For now, displaying key fields
        print("Application details displayed")
        print("-" * 60)


    def handle_tasks(self):
        """Handle TASKS menu option."""
        today = date.today()

        # Check backlog
        backlog_tasks = self.db.get_backlog_tasks(today)

        if backlog_tasks:
            print(f"\n📋 You have {len(backlog_tasks)} overdue task(s) in your backlog!")
            response = Input.get_yes_no_exit("\nWould you like to view your backlog first? (Y/N/X): ")

            if response == 'X':
                Display.exit_to_menu()
                return

            if response == 'Y':
                self._process_backlog(backlog_tasks, today)
                return

        # Process today's tasks
        self._process_daily_tasks(today)


    def _process_backlog(self, backlog_tasks: List[Tuple], today: date):
        """Process backlog tasks."""
        print(f"\n📋 Backlog - Overdue Tasks")
        print("-" * 60)

        for task in backlog_tasks:
            _display_backlog_task(task, today)

        print("=" * 60)

        # Process selected task
        while True:
            task_id = Input.get_number("\nEnter the ID of the task you would like to complete (or X to exit): ",
                                       1, 999999)
            if task_id is None:
                Display.exit_to_menu()
                break

            selected = next((t for t in backlog_tasks if t[0] == task_id), None)
            if selected:
                if not self.task_processor.process_task_completion(selected, today):
                    break
            else:
                Display.invalid_number()


    def _process_daily_tasks(self, today: date):
        """Process today's tasks."""
        daily_tasks = self.db.get_daily_tasks(today)

        if not daily_tasks:
            print("\n🎉 No tasks for today!")
            return

        print(f"\n🗓️ Tasks for {today.strftime('%A, %B %d, %Y')}")
        print("-" * 60)

        incomplete_tasks = []

        for task in daily_tasks:
            if not self._process_daily_task(task, today, incomplete_tasks):
                break

        # Show incomplete tasks
        if incomplete_tasks:
            print("\n📋 Today's Incomplete Tasks:")
            print("-" * 60)
            for job_title, company, task_name in incomplete_tasks:
                print(f"📌 {job_title} @ {company} - {task_name}")
            print("-" * 60)


    def _process_daily_task(self, task: Tuple, today: date, incomplete_tasks: List) -> bool:
        """Process a single daily task. Returns False if user exits."""
        (app_id, job_title, company, next_action, _, contact_name, contact_details,
         current_status, _, interview_date, interview_time, second_interview_date,
         final_interview_date, is_priority) = task

        # Determine task type
        if interview_date == today or second_interview_date == today or final_interview_date == today:
            due_type = "Interview"
        else:
            due_type = "Follow Up"

        # Display task
        priority_indicator = " ‼️" if is_priority else ""
        print(f"📌 {job_title} @ {company}{priority_indicator}")
        print(f"   → Current Status: {Display.format_status(current_status)}")
        if next_action:
            print(f"   → Task: {next_action.replace('_', ' ').title()}")
        print(f"   → Type: {due_type}")
        if interview_time:
            print(f"   → Interview Time: {interview_time.strftime('%I:%M %p')}")

        # Check contact info
        if not ContactManager.prompt_for_contact_info(self.db, app_id, contact_name, contact_details):
            return False

        # Task completion
        response = Input.get_yes_no_exit("✅ Mark this task as completed? (Y/N/X): ")
        if response == 'X':
            return False

        if response == 'Y':
            new_status = self.db.update_status(app_id, next_action)
            if new_status:
                print(f"\n✅ Status auto-updated to: {Display.format_status(new_status)}\n")
            else:
                print("\n✅ Task marked as completed\n")
        else:
            incomplete_tasks.append((job_title, company, next_action or "Follow up"))

        # Manual status update
        response = Input.get_yes_no_exit("\n✏️ Would you like to manually update the application status? (Y/N/X): ")
        if response == 'X':
            return False

        if response == 'Y':
            new_status = self.db.manual_status_update(app_id)
            if new_status:
                print(f"\n✅ Status manually updated to: {Display.format_status(new_status)}\n")
            else:
                print("\n⏭️ Skipped status update.\n")
        else:
            print("\n⏭️ Skipped status update.\n")

        return True


    def handle_enter(self):
        """Handle ENTER menu option - add new application or recruiter contact."""
        print("\nWhat would you like to track?")
        print("1. Job Application (I applied)")
        print("2. Recruiter Outreach (they contacted me)")

        choice = Input.get_number("\nSelect option (1-2, or X to exit): ", 1, 2)
        if choice is None:
            Display.exit_to_menu()
            return

        if choice == 1:
            self._handle_job_application()
        elif choice == 2:
            self._handle_recruiter_outreach()


    def _handle_job_application(self):
        """Handle adding a job application (existing flow)."""
        print("\nEnter your new application details:")

        job_title = Input.get_string("Job title: ", allow_empty=False)
        if job_title is None:
            Display.exit_to_menu()
            return

        company = Input.get_string("Company: ", allow_empty=False)
        if company is None:
            Display.exit_to_menu()
            return

        software = Input.get_string("How did you apply (LinkedIn, Workday, Greenhouse, company website etc): ")
        notes = Input.get_string("Any notes about this role? (optional): ")

        is_priority = Input.get_yes_no("Mark this job as priority? (Y/N): ") == 'Y'

        print("Optional now, but do your research! 🔎")
        contact_name = Input.get_string("Contact Name: ")
        contact_details = Input.get_string("Contact Details: ")

        self.db.add_application(job_title, company, software, notes,
                                contact_name, contact_details, is_priority)
        print("\n✅ Application added! I'll remind you when you have tasks related to this job. 😊")


    def _handle_recruiter_outreach(self):
        """Handle adding a recruiter contact."""
        print("\nEnter recruiter contact details:")

        recruiter_name = Input.get_string("Recruiter name: ", allow_empty=False)
        if recruiter_name is None:
            Display.exit_to_menu()
            return

        recruiting_company = Input.get_string("Recruiting company (or hiring company if internal): ", allow_empty=False)
        if recruiting_company is None:
            Display.exit_to_menu()
            return

        contact_details = Input.get_string("Contact details (email/phone/LinkedIn): ")

        initial_call_date = Input.get_string("Date of initial contact (YYYY-MM-DD) or press enter for today: ")
        if initial_call_date == "":
            initial_call_date = date.today().strftime('%Y-%m-%d')

        initial_call_time = Input.get_string("Time of call (HH:MM, optional): ")

        notes = Input.get_string("Any notes about the conversation? (optional): ")

        is_priority = Input.get_yes_no("Mark as priority? (Y/N): ") == 'Y'

        # Add recruiter entry
        self.db.add_recruiter_contact(
            recruiter_name, recruiting_company, contact_details,
            initial_call_date, initial_call_time, notes, is_priority
        )

        print("\n✅ Recruiter contact added!")
        print("💡 Tip: You can link a specific role to this recruiter later via the UPDATE menu.")


    def _handle_update_menu(self, app_id: int):
        """Handle the update submenu."""
        print("\nWhat do you want to update?")
        print("1. Application status")
        print("2. Update contact info")
        print("3. Schedule interview")
        print("4. Notes")
        print("5. Update priority")
        print("6. Delete Entry")

        choice = Input.get_number("\nField to update (1-6, or X to exit): ", 1, 6)
        if choice is None:
            Display.exit_to_menu()
            return

        if choice == 1:
            self._update_status(app_id)
        elif choice == 2:
            self._update_contact(app_id)
        elif choice == 3:
            self._update_interview(app_id)
        elif choice == 4:
            self._update_notes(app_id)
        elif choice == 5:
            self._update_priority(app_id)
        elif choice == 6:
            self._delete_application(app_id)

    def _update_status(self, app_id: int):
        """Update application status."""
        new_status = self.db.manual_status_update(app_id)
        if new_status:
            print(f"\n✅ Status updated to: {Display.format_status(new_status)}")
        else:
            print("\n⏭️ Status update cancelled.")

    def _update_contact(self, app_id: int):
        """Update contact information."""
        contact_name = Input.get_string("Contact name: ")
        if contact_name is None:
            return
        contact_details = Input.get_string("Contact email/phone/URL: ")
        if contact_details is None:
            return
        self.db.update_contact_info(app_id, contact_name, contact_details)
        print("\n✅ Follow-up contact updated.")

    def _update_interview(self, app_id: int):
        """Update interview details."""
        interview_date = Input.get_string("Enter interview date (YYYY-MM-DD): ")
        if interview_date is None:
            return
        interview_time = Input.get_string("Enter interview time (HH:MM): ")
        interview_name = Input.get_string("Interviewer name: ")
        if interview_name is None:
            return
        prep_notes = Input.get_string("Any prep notes? (optional): ")

        self.db.update_interview(app_id, interview_date, interview_time,
                                 interview_name, prep_notes)
        print("\n✅ Interview details updated.")

    def _update_notes(self, app_id: int):
        """Update notes."""
        self.db.cursor.execute("SELECT job_notes FROM application_tracking WHERE id = %s", (app_id,))
        result = self.db.cursor.fetchone()
        current_notes = result[0] if result and result[0] else ""

        if current_notes:
            print(f"\nCurrent notes: {current_notes}")
        else:
            print("\nNo existing notes for this application.")

        new_notes = Input.get_string("\nEnter additional notes (or X to cancel): ")
        if new_notes is None:
            Display.exit_to_menu()
            return

        self.db.update_notes(app_id, new_notes, append=True)
        print("\n✅ Notes updated.")

    def _update_priority(self, app_id: int):
        """Update priority status."""
        response = Input.get_yes_no_exit("Mark as priority? (Y/N/X): ")
        if response == 'X':
            Display.exit_to_menu()
            return

        is_priority = response == 'Y'
        self.db.update_priority(app_id, is_priority)

        if is_priority:
            print("\n✅ Application marked as priority.")
        else:
            print("\n✅ Priority removed from application.")

    def _delete_application(self, app_id: int):
        """Delete an application."""
        self.db.cursor.execute(
            """SELECT job_title, company, application_status 
               FROM application_tracking WHERE id = %s""",
            (app_id,)
        )
        app_details = self.db.cursor.fetchone()

        if not app_details:
            print("\n❌ Application not found.")
            return

        job_title, company, status = app_details
        print(f"\n⚠️  You are about to delete:")
        print(f"   Job: {job_title}")
        print(f"   Company: {company}")
        print(f"   Status: {status}")

        response = Input.get_yes_no_exit("\nAre you sure you want to delete this application? (Y/N/X): ")
        if response != 'Y':
            Display.deletion_cancelled()
            return

        while True:
            confirmation = input("This action cannot be undone. Type 'DELETE' to confirm (or X to cancel): ").strip()
            if confirmation == "DELETE":
                self.db.delete_application(app_id)
                print(f"\n✅ Application for {job_title} @ {company} has been deleted.")
                break
            elif confirmation.upper() in ['X', 'N', 'NO']:
                Display.deletion_cancelled()
                break
            else:
                print("\n❌ Please type 'DELETE' exactly to confirm, or 'X'/'N' to cancel")

    @staticmethod
    def handle_tips():
        """Display job search tips."""
        print("\n💡 Job Search Tips:")
        print(
            "📩 FOLLOW UP! You are 78% more likely to land an interview if you reach out to a recruiter or hiring manager after you apply.")
        print(
            "✏️ TAKE NOTES! You should already know why you want to work for the company and about their mission BEFORE speaking with someone from the company.")
        print("🔑 Confidence is Key! You know you deserve this job and focus on YOU, not anyone else!")
        print("💻 Keep applying, keep trying. It will not be this way forever.")



# MAIN APPLICATION #
# ================ #
def main():
    """Main application loop."""
    Display.intro()

    # Initialize database schema (safe to run multiple times)
    with DatabaseConnection(DB_CONFIG, initialize=True) as (conn, cursor):
        pass  # Schema initialization happens in __enter__

    # Run main application
    with DatabaseConnection(DB_CONFIG) as (conn, cursor):
        db = ApplicationDB(cursor, conn)
        menu = MenuHandler(db)

        while True:
            Display.main_menu()
            selection = input("\nAction: ").strip().upper()

            if selection == "VIEW":
                menu.handle_view()
            elif selection == "TASKS":
                menu.handle_tasks()
            elif selection == "ENTER":
                menu.handle_enter()
            elif selection == "UPDATE":
                menu.handle_update()
            elif selection == "TIPS":
                menu.handle_tips()
            elif selection == "BYE":
                print("\n👋 Goodbye! Check back again soon!")
                break
            else:
                print("\n❌ Invalid selection. 🥲 Please try again from the main menu.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Session interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        sys.exit(1)