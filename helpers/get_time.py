import time
import datetime


def get_post_time(postTimestamp):
    time1 = datetime.datetime.fromtimestamp(postTimestamp)
    time2 = datetime.datetime.fromtimestamp(int(time.time()))
    timeDiff = time2 - time1

    sec = int(timeDiff.total_seconds())
    min = int(timeDiff.total_seconds() / 60)
    hr = int(timeDiff.total_seconds() / 3600)
    day = int(timeDiff.total_seconds() / 86400)
    mon = int(timeDiff.total_seconds() / 2592000)
    yr = int(timeDiff.total_seconds() / 31536000)

    if yr > 0:
        return f"{yr}yr ago"
    elif mon > 0:
        return f"{mon}mon ago"
    elif day > 0:
        return f"{day}d ago"
    elif hr > 0:
        return f"{hr}h ago"
    elif min > 0:
        return f"{min}m ago"
    elif sec > 0:
        return f"{sec}s ago"
    else:
        return "Just now"
