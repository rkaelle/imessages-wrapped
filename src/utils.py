"""
Utility functions for iMessage Wrapped
"""

from datetime import datetime, timedelta
import re
from typing import Tuple


def get_time_period(period: str = "past_year") -> Tuple[datetime, datetime]:
    """
    Get start and end dates for analysis period

    Args:
        period: Either "past_year" or "all_time"

    Returns:
        Tuple of (start_date, end_date)
    """
    end_date = datetime.now()

    if period == "past_year":
        start_date = end_date - timedelta(days=365)
    else:  # all_time
        start_date = datetime(2001, 1, 1)  # Apple's epoch

    return start_date, end_date


def format_number(num: int) -> str:
    """
    Format large numbers in human-readable format

    Args:
        num: Number to format

    Returns:
        Formatted string (e.g., "1.2K", "3.4M")
    """
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return str(num)


def anonymize_contact(contact: str, anonymize: bool = False) -> str:
    """
    Anonymize phone numbers or emails for sharing

    Args:
        contact: Phone number or email address
        anonymize: Whether to anonymize

    Returns:
        Original or anonymized contact
    """
    if not anonymize or not contact:
        return contact

    # Email
    if "@" in contact:
        parts = contact.split("@")
        if len(parts[0]) > 2:
            return f"{parts[0][:2]}...@{parts[1]}"
        return f"{parts[0][0]}...@{parts[1]}"

    # Phone number
    # Remove all non-digits
    digits = re.sub(r'\D', '', contact)

    if len(digits) >= 4:
        return f"({digits[:3]}) ***-{digits[-4:]}"
    elif len(digits) > 0:
        return f"***{digits[-2:]}"

    return "Anonymous"


def get_contact_display_name(phone_number: str) -> str:
    """
    Get a display name for a contact

    Args:
        phone_number: Phone number or email

    Returns:
        Formatted display name (from Contacts if available, otherwise formatted number)
    """
    if not phone_number:
        return "Unknown"
    
    # Try to get real name from Contacts
    try:
        from .contacts import get_contact_resolver
        resolver = get_contact_resolver()
        contact_name = resolver.get_contact_name(phone_number)
        if contact_name:
            return contact_name
    except Exception:
        pass  # Fail gracefully if contacts not available

    # Fall back to formatting the phone/email
    # If it's an email, use the part before @
    if "@" in phone_number:
        return phone_number.split("@")[0]

    # Format phone number
    digits = re.sub(r'\D', '', phone_number)

    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    elif len(digits) > 10:
        return f"+{digits[:len(digits)-10]} ({digits[-10:-7]}) {digits[-7:-4]}-{digits[-4:]}"

    return phone_number


def calculate_response_time(sent_time: datetime, received_time: datetime) -> float:
    """
    Calculate response time in minutes

    Args:
        sent_time: When message was sent
        received_time: When response was received

    Returns:
        Response time in minutes, or None if invalid
    """
    if not sent_time or not received_time:
        return None

    if received_time < sent_time:
        return None

    delta = received_time - sent_time
    return delta.total_seconds() / 60


def format_duration(minutes: float) -> str:
    """
    Format duration in human-readable format

    Args:
        minutes: Duration in minutes

    Returns:
        Formatted string (e.g., "2m", "1h 30m", "2d 3h")
    """
    if minutes is None or minutes < 0:
        return "N/A"

    if minutes < 1:
        return f"{int(minutes * 60)}s"
    elif minutes < 60:
        return f"{int(minutes)}m"
    elif minutes < 1440:  # Less than a day
        hours = int(minutes / 60)
        mins = int(minutes % 60)
        if mins > 0:
            return f"{hours}h {mins}m"
        return f"{hours}h"
    else:  # Days
        days = int(minutes / 1440)
        hours = int((minutes % 1440) / 60)
        if hours > 0:
            return f"{days}d {hours}h"
        return f"{days}d"


def extract_emojis(text: str) -> list:
    """
    Extract emojis from text

    Args:
        text: Message text

    Returns:
        List of emojis found
    """
    if not text:
        return []

    # Unicode emoji ranges
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # extended symbols
        "]+",
        flags=re.UNICODE
    )

    return emoji_pattern.findall(text)


def get_time_of_day_label(hour: int) -> str:
    """
    Get label for time of day

    Args:
        hour: Hour (0-23)

    Returns:
        Label like "Night Owl", "Early Bird", etc.
    """
    if 0 <= hour < 6:
        return "Night Owl"
    elif 6 <= hour < 12:
        return "Early Bird"
    elif 12 <= hour < 17:
        return "Afternoon Texter"
    elif 17 <= hour < 21:
        return "Evening Chatter"
    else:
        return "Night Texter"


def classify_responder(median_minutes: float) -> str:
    """
    Classify response speed

    Args:
        median_minutes: Median response time in minutes

    Returns:
        Classification label
    """
    if median_minutes is None:
        return "Unknown"
    elif median_minutes < 5:
        return "Instant Responder"
    elif median_minutes < 30:
        return "Quick Responder"
    elif median_minutes < 180:  # 3 hours
        return "Moderate Responder"
    elif median_minutes < 1440:  # 1 day
        return "Slow Responder"
    else:
        return "Ghost"
