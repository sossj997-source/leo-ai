def get_current_ist_time() -> str:
    """Return the current time in IST (UTC+5:30) as a formatted string."""
    try:
        from datetime import datetime, timezone, timedelta
        ist_tz = timezone(timedelta(hours=5, minutes=30), name="IST")
        now_ist = datetime.now(ist_tz)
        return now_ist.strftime("%Y-%m-%d %H:%M:%S %Z%z")
    except Exception as e:
        return f"Error: {e}"