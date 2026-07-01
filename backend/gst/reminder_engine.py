"""
Automated Reminders Engine

Sends payment reminders via:
- Email (SMTP)
- SMS (Twilio)
- Push notifications
- In-app notifications
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class ReminderType(str, Enum):
    """Types of reminders"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class ReminderTiming(str, Enum):
    """When to send reminders"""
    ADVANCE_7_DAYS = "7_days_before"
    ADVANCE_3_DAYS = "3_days_before"
    ADVANCE_1_DAY = "1_day_before"
    ON_DUE_DATE = "on_due_date"
    OVERDUE_1_DAY = "1_day_overdue"
    OVERDUE_7_DAYS = "7_days_overdue"


@dataclass
class ReminderTemplate:
    """Email/SMS template"""
    subject: str
    body: str
    type: ReminderType


class ReminderEngine:
    """Manages payment reminders"""

    # Email templates
    EMAIL_TEMPLATES = {
        ReminderTiming.ADVANCE_7_DAYS: ReminderTemplate(
            subject="Payment Reminder: GST {return_type} Due in 7 Days",
            body="""
Dear {name},

This is a friendly reminder that your {return_type} return payment is due on {due_date}.

Details:
- Return Type: {return_type}
- Period: {period}
- Tax Payable: ₹{tax_amount:,.0f}
- Due Date: {due_date}
- Days Remaining: 7

Please ensure timely payment to avoid late charges.

Interest on Late Payment: 18% per annum (0.05% per day)

Best regards,
GSTAgent Payment Tracking
            """,
            type=ReminderType.EMAIL
        ),

        ReminderTiming.ADVANCE_3_DAYS: ReminderTemplate(
            subject="URGENT: GST {return_type} Payment Due in 3 Days",
            body="""
Dear {name},

Your {return_type} return payment is due in just 3 days ({due_date}).

Details:
- Return Type: {return_type}
- Period: {period}
- Tax Payable: ₹{tax_amount:,.0f}
- Due Date: {due_date}
- Days Remaining: 3

Interest Penalty: 18% per annum (0.05% per day)

Please make payment immediately to avoid penalties.

Best regards,
GSTAgent Payment Tracking
            """,
            type=ReminderType.EMAIL
        ),

        ReminderTiming.ON_DUE_DATE: ReminderTemplate(
            subject="CRITICAL: GST {return_type} Due TODAY",
            body="""
Dear {name},

Your {return_type} return payment is DUE TODAY ({due_date}).

Details:
- Return Type: {return_type}
- Period: {period}
- Tax Payable: ₹{tax_amount:,.0f}
- Due Date: {due_date}
- Status: DUE NOW

Late payment will incur interest at 18% per annum.

Please make payment immediately.

Best regards,
GSTAgent Payment Tracking
            """,
            type=ReminderType.EMAIL
        ),

        ReminderTiming.OVERDUE_1_DAY: ReminderTemplate(
            subject="OVERDUE: GST {return_type} Payment 1 Day Late",
            body="""
Dear {name},

Your {return_type} return payment is now OVERDUE by 1 day.

Details:
- Return Type: {return_type}
- Period: {period}
- Original Due Date: {due_date}
- Days Overdue: 1
- Interest Accrued: ₹{interest_amount:,.0f}
- Total Due: ₹{total_due:,.0f}

Please make urgent payment to minimize interest penalties.

Best regards,
GSTAgent Payment Tracking
            """,
            type=ReminderType.EMAIL
        ),

        ReminderTiming.OVERDUE_7_DAYS: ReminderTemplate(
            subject="CRITICAL OVERDUE: GST {return_type} Payment 7 Days Late",
            body="""
Dear {name},

Your {return_type} return payment is now OVERDUE by 7 days.

Details:
- Return Type: {return_type}
- Period: {period}
- Original Due Date: {due_date}
- Days Overdue: 7
- Interest Accrued: ₹{interest_amount:,.0f}
- Total Due: ₹{total_due:,.0f}

URGENT ACTION REQUIRED:
Please make immediate payment to stop accumulating interest penalties.

Best regards,
GSTAgent Payment Tracking
            """,
            type=ReminderType.EMAIL
        ),
    }

    # SMS templates (shorter)
    SMS_TEMPLATES = {
        ReminderTiming.ADVANCE_7_DAYS:
            "GSTAgent: Your {return_type} (Period {period}) is due on {due_date}. Tax: ₹{tax_amount:,.0f}. Reply STOP to unsubscribe.",

        ReminderTiming.ADVANCE_3_DAYS:
            "URGENT: {return_type} (Period {period}) due in 3 days ({due_date}). Tax: ₹{tax_amount:,.0f}. Late interest: 18% p.a.",

        ReminderTiming.ON_DUE_DATE:
            "CRITICAL: {return_type} (Period {period}) due TODAY ({due_date}). Tax: ₹{tax_amount:,.0f}. Pay now to avoid penalties.",

        ReminderTiming.OVERDUE_1_DAY:
            "OVERDUE: {return_type} (Period {period}) is 1 day late. Interest accrued: ₹{interest_amount:,.0f}. Pay now.",

        ReminderTiming.OVERDUE_7_DAYS:
            "CRITICAL: {return_type} (Period {period}) is 7 days overdue. Total due: ₹{total_due:,.0f}. Urgent payment needed.",
    }

    @staticmethod
    def get_reminder_schedule(due_date: str) -> dict:
        """
        Get reminder schedule for a due date.

        Args:
            due_date: Due date in YYYY-MM-DD format

        Returns:
            Schedule with all reminder timings
        """
        due_datetime = datetime.fromisoformat(due_date)
        today = datetime.now()

        schedule = {}
        for timing in ReminderTiming:
            reminder_date = None

            if timing == ReminderTiming.ADVANCE_7_DAYS:
                reminder_date = due_datetime - timedelta(days=7)
            elif timing == ReminderTiming.ADVANCE_3_DAYS:
                reminder_date = due_datetime - timedelta(days=3)
            elif timing == ReminderTiming.ADVANCE_1_DAY:
                reminder_date = due_datetime - timedelta(days=1)
            elif timing == ReminderTiming.ON_DUE_DATE:
                reminder_date = due_datetime
            elif timing == ReminderTiming.OVERDUE_1_DAY:
                reminder_date = due_datetime + timedelta(days=1)
            elif timing == ReminderTiming.OVERDUE_7_DAYS:
                reminder_date = due_datetime + timedelta(days=7)

            schedule[timing.value] = {
                "timing": timing.value,
                "date": reminder_date.strftime("%Y-%m-%d"),
                "status": "pending" if reminder_date > today else "due" if reminder_date == today.date() else "overdue"
            }

        return schedule

    @staticmethod
    def generate_email(
        timing: ReminderTiming,
        recipient_email: str,
        recipient_name: str,
        return_type: str,
        period: str,
        tax_amount: float,
        due_date: str,
        interest_amount: float = 0,
        total_due: float = 0
    ) -> tuple:
        """
        Generate email reminder.

        Returns:
            (subject, body, to_email)
        """
        template = ReminderEngine.EMAIL_TEMPLATES.get(
            timing,
            ReminderEngine.EMAIL_TEMPLATES[ReminderTiming.ADVANCE_7_DAYS]
        )

        subject = template.subject.format(
            return_type=return_type,
            period=period,
            due_date=due_date
        )

        body = template.body.format(
            name=recipient_name,
            return_type=return_type,
            period=period,
            tax_amount=tax_amount,
            due_date=due_date,
            interest_amount=interest_amount,
            total_due=total_due
        )

        return subject, body, recipient_email

    @staticmethod
    def generate_sms(
        timing: ReminderTiming,
        return_type: str,
        period: str,
        tax_amount: float,
        due_date: str,
        interest_amount: float = 0,
        total_due: float = 0
    ) -> str:
        """Generate SMS reminder"""
        template = ReminderEngine.SMS_TEMPLATES.get(
            timing,
            ReminderEngine.SMS_TEMPLATES[ReminderTiming.ADVANCE_7_DAYS]
        )

        sms_text = template.format(
            return_type=return_type,
            period=period,
            tax_amount=tax_amount,
            due_date=due_date,
            interest_amount=interest_amount,
            total_due=total_due
        )

        return sms_text

    @staticmethod
    def send_email(
        subject: str,
        body: str,
        to_email: str,
        sender_email: str = "noreply@gstagent.co.in",
        smtp_password: str = None
    ) -> bool:
        """
        Send email reminder (requires SMTP configuration).

        Note: In production, configure SMTP server details
        """
        try:
            # For production, configure your SMTP server
            # smtp_server = smtplib.SMTP("smtp.gmail.com", 587)
            # smtp_server.starttls()
            # smtp_server.login(sender_email, smtp_password)

            # Create message
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            # For demo, just return True (production would send via SMTP)
            return True

        except Exception as e:
            print(f"Email error: {e}")
            return False

    @staticmethod
    def send_sms(phone_number: str, message: str) -> bool:
        """
        Send SMS reminder (requires Twilio configuration).

        Note: In production, configure Twilio credentials
        """
        try:
            # from twilio.rest import Client
            # account_sid = "YOUR_TWILIO_ACCOUNT_SID"
            # auth_token = "YOUR_TWILIO_AUTH_TOKEN"
            # client = Client(account_sid, auth_token)

            # message = client.messages.create(
            #     body=message,
            #     from_="+1234567890",
            #     to=phone_number
            # )

            # For demo, just return True (production would send via Twilio)
            return True

        except Exception as e:
            print(f"SMS error: {e}")
            return False

    @staticmethod
    def send_push_notification(
        user_id: str,
        title: str,
        body: str,
        data: dict = None
    ) -> bool:
        """
        Send push notification (requires Firebase/OneSignal).

        Note: In production, configure push notification service
        """
        try:
            # from firebase_admin import messaging
            # message = messaging.Message(
            #     notification=messaging.Notification(title=title, body=body),
            #     data=data or {},
            # )
            # messaging.send(message)

            # For demo, just return True
            return True

        except Exception as e:
            print(f"Push notification error: {e}")
            return False

    @staticmethod
    def send_in_app_notification(
        user_id: str,
        notification_type: str,
        title: str,
        body: str,
        action_url: str = None
    ) -> bool:
        """
        Create in-app notification (store in database).

        Note: In production, save to database
        """
        notification = {
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "body": body,
            "action_url": action_url,
            "created_at": datetime.now().isoformat(),
            "read": False
        }

        # In production: save to database
        # db.notifications.insert_one(notification)

        return True


class ReminderScheduler:
    """Schedules and manages reminders"""

    @staticmethod
    def schedule_payment_reminders(
        user_id: str,
        return_type: str,
        period: str,
        tax_amount: float,
        due_date: str,
        recipient_email: str = None,
        phone_number: str = None,
        reminder_methods: List[ReminderType] = None
    ) -> dict:
        """
        Schedule reminders for a payment.

        Args:
            user_id: User ID
            return_type: GSTR-1, GSTR-3B, etc
            period: Period (MMYYYY)
            tax_amount: Tax amount
            due_date: Due date (YYYY-MM-DD)
            recipient_email: Email address
            phone_number: Phone number
            reminder_methods: Methods to use (email, SMS, push, in_app)

        Returns:
            Scheduled reminders
        """
        reminder_methods = reminder_methods or [
            ReminderType.EMAIL,
            ReminderType.IN_APP
        ]

        schedule = ReminderEngine.get_reminder_schedule(due_date)
        scheduled_reminders = {}

        for timing_key, timing_info in schedule.items():
            timing = ReminderTiming(timing_key)

            reminders = {
                "timing": timing.value,
                "date": timing_info["date"],
                "status": timing_info["status"],
                "methods": {}
            }

            # Generate reminders for each method
            for method in reminder_methods:
                if method == ReminderType.EMAIL and recipient_email:
                    subject, body, to_email = ReminderEngine.generate_email(
                        timing=timing,
                        recipient_email=recipient_email,
                        recipient_name="User",
                        return_type=return_type,
                        period=period,
                        tax_amount=tax_amount,
                        due_date=due_date
                    )
                    reminders["methods"][ReminderType.EMAIL.value] = {
                        "subject": subject,
                        "to": to_email,
                        "status": "scheduled"
                    }

                elif method == ReminderType.SMS and phone_number:
                    sms_text = ReminderEngine.generate_sms(
                        timing=timing,
                        return_type=return_type,
                        period=period,
                        tax_amount=tax_amount,
                        due_date=due_date
                    )
                    reminders["methods"][ReminderType.SMS.value] = {
                        "text": sms_text,
                        "to": phone_number,
                        "status": "scheduled"
                    }

                elif method == ReminderType.IN_APP:
                    reminders["methods"][ReminderType.IN_APP.value] = {
                        "title": f"{return_type} Payment Due",
                        "status": "scheduled"
                    }

            scheduled_reminders[timing_key] = reminders

        return {
            "user_id": user_id,
            "return_type": return_type,
            "period": period,
            "due_date": due_date,
            "scheduled_reminders": scheduled_reminders
        }
