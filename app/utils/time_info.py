from datetime import datetime

def get_time_information() -> str:
    return datetime.now().strftime("%A, %B %d, %Y, %I:%M %p %Z")