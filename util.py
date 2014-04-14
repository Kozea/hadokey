from datetime import datetime
import calendar

def is_in_weekend(day):
    """Return True if day is in week-end.
    
    >>> is_in_weekend(1397426400.0)
    False
    
    >>> is_in_weekend(1397253600.0)
    True
     """
    date = datetime.fromtimestamp(day)
    return calendar.weekday(date.year, date.month, date.day) in (5, 6)
    
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
