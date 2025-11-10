import datetime

def log_titanic_timestamp():
    """
    Logs the current timestamp in a human-readable format with milliseconds.
    """
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    milliseconds = int(current_time.microsecond / 1000)
    return f"{formatted_time}.{milliseconds:03d}"