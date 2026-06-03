from datetime import date, time, datetime, timedelta
from typing import List, Tuple


MORNING_START = time(9, 30)
MORNING_END = time(11, 30)
AFTERNOON_START = time(13, 0)
AFTERNOON_END = time(15, 0)


def is_trading_time(t: time) -> bool:
    return (MORNING_START <= t <= MORNING_END) or (AFTERNOON_START <= t <= AFTERNOON_END)


def generate_windows(day: date, window_minutes: int) -> List[Tuple[datetime, datetime]]:
    windows = []
    step = timedelta(minutes=window_minutes)

    sessions = [
        (datetime.combine(day, MORNING_START), datetime.combine(day, MORNING_END)),
        (datetime.combine(day, AFTERNOON_START), datetime.combine(day, AFTERNOON_END)),
    ]

    for session_start, session_end in sessions:
        cursor = session_start
        while cursor + step <= session_end:
            windows.append((cursor, cursor + step))
            cursor += step

    return windows


def minutes_to_close(dt: datetime) -> float:
    t = dt.time()
    day = dt.date()
    if MORNING_START <= t <= MORNING_END:
        close = datetime.combine(day, AFTERNOON_END)
        lunch_break = timedelta(hours=1, minutes=30)
        remaining_morning = datetime.combine(day, MORNING_END) - dt
        return (remaining_morning + timedelta(hours=2) ).total_seconds() / 60
    elif AFTERNOON_START <= t <= AFTERNOON_END:
        close = datetime.combine(day, AFTERNOON_END)
        return (close - dt).total_seconds() / 60
    return 0.0
