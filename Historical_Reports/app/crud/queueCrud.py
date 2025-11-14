# app/crud.py
from fastapi import HTTPException
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app import schemas
from app.utils import seconds_to_hms
from datetime import datetime, timedelta
import pytz
from typing import List, Union
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from sqlalchemy import text
from typing import List, Dict

# --------------------------------------- Queue metrics ---------------------------------->

# 15 minutes time intervals

# Working with the cdr table.
def fetch_unique_queue_names(db: Session, user_time_zone: str) -> list[str]:
    user_tz = pytz.timezone(user_time_zone)
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    print(f"Start Time (UTC): {start_time_utc}")
    print(f"End Time (UTC): {end_time_utc}")

    # Fetch distinct queue names from the 'cdr' table
    query = text("""
        SELECT DISTINCT cc_queue
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        })
        data = result.fetchall()
        print(f"Fetched {len(data)} unique queues from the database.")
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    if not data:
        print("No data found for the specified time range.")
        return []

    # Collect unique queue names
    queue_names = {row[0] for row in data}  # Using a set to ensure uniqueness

    print("Unique queue names:", queue_names)  # Check what names were added
    return list(queue_names)  # Convert set back to list if needed

# Working with the cdr table.
def fetch_service_level_60_seconds_per_queue_last_15_minutes(db: Session, user_time_zone: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT 
            cc_queue,
            FLOOR(SUM(CASE WHEN (answer_stamp - start_stamp) <= interval '60 seconds' THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(COUNT(*), 0)) AS service_level_60_seconds,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        print(f"Executing query with start_time: {start_time_utc}, end_time: {end_time_utc}")
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        print(f"Query results: {results}")
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"service_level_60_seconds": {"error": str(e)}}]

    service_levels = []
    
    for row in results:
        service_levels.append({
            "queue": row[0],  # cc_queue
            "service_level_60_seconds": f"{int(row[1])}%",  # Service level rounded down to nearest whole number
            "total_calls": row[2]  # Total calls for the queue
        })

    return service_levels

# Working with the cdr table.
def fetch_service_level_120_seconds_per_queue_last_15_minutes(db: Session, user_time_zone: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT 
            cc_queue,
            FLOOR(SUM(CASE WHEN (answer_stamp - start_stamp) <= interval '120 seconds' THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(COUNT(*), 0)) AS service_level_120_seconds,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return []  # Return an empty list on error

    service_levels = []
    
    for row in results:
        service_levels.append({
            "queue": row[0],  # cc_queue
            "service_level_120_seconds": f"{int(row[1])}%",  # Service level rounded down to nearest whole number
            "total_calls": row[2]  # Total calls for the queue
        })

    return service_levels if service_levels else []  # Return empty list if no data

# Working with the cdr table.
def fetch_average_after_contact_work_time_for_queues(db: Session, user_time_zone: str) -> list[dict]:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert the user's local times to UTC for querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT 
            cc_queue,
            SUM(COALESCE(end_stamp - answer_stamp, interval '0 seconds')) AS total_acw,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        # Execute the query with UTC timestamps
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"queue": None, "avg_time": 0, "avg_time_formatted": "00:00:00"}]

    avg_aacw_results = []

    for row in results:
        total_acw = row[1] if row[1] is not None else timedelta(seconds=0)
        total_calls = row[2] if row[2] is not None else 0

        # Calculate average ACW, handling division by zero
        if total_calls > 0:
            avg_acw_seconds = total_acw.total_seconds() / total_calls
        else:
            avg_acw_seconds = 0  # No calls, so average ACW is 0

        # Convert average seconds to HH:MM:SS format
        avg_acw_formatted = seconds_to_hms(int(avg_acw_seconds))

        avg_aacw_results.append({
            "queue": row[0],  # cc_queue
            "avg_time": avg_acw_seconds,
            "avg_time_formatted": avg_acw_formatted
        })

    return avg_aacw_results

# Working with the cdr table.
def fetch_average_agent_interaction_time_for_queues(db: Session, user_time_zone: str) -> list[dict]:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert the user's local times to UTC for querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    # Query to fetch the average agent interaction time and total calls per queue in the last 15 minutes
    query = text("""
        SELECT 
            cc_queue,
            SUM(EXTRACT(EPOCH FROM (end_stamp - answer_stamp))) AS total_interaction_time,  -- Sum of interaction time in seconds
            COUNT(*) AS total_calls  -- Total number of calls
        FROM cdr
        WHERE answer_stamp IS NOT NULL  -- Only consider answered calls
        AND timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL  -- Filter by non-null queues
        GROUP BY cc_queue
    """)

    try:
        # Execute the query with UTC timestamps
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"avg_time": 0, "avg_time_formatted": "00:00:00", "total_calls": 0}]

    avg_interaction_times = []

    # Loop through the results to calculate the average interaction time per queue
    for row in results:
        total_interaction_time = row[1]  # Total interaction time in seconds
        total_calls = row[2]  # Total number of calls

        # Calculate the average interaction time in seconds
        avg_interaction_seconds = total_interaction_time / total_calls if total_calls > 0 else 0

        # Convert the average time to HH:MM:SS format
        avg_interaction_formatted = seconds_to_hms(int(avg_interaction_seconds))

        avg_interaction_times.append({
            "queue": row[0],  # cc_queue
            "avg_time": avg_interaction_seconds,
            "avg_time_formatted": avg_interaction_formatted,
            "total_calls": total_calls
        })

    return avg_interaction_times

# Working with the cdr table. 
def fetch_average_queue_answer_time_per_queue(db: Session, user_time_zone: str) -> dict:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    # Print the time range being used for the query
    print(f"Querying data from {start_time_utc} to {end_time_utc}")

    query = text("""
        SELECT cc_queue, AVG(EXTRACT(EPOCH FROM (answer_stamp - start_stamp))) AS avg_queue_answer_time
        FROM cdr
        WHERE answer_stamp IS NOT NULL
        AND start_stamp IS NOT NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Print the raw result for debugging
        print(f"Raw result: {result}")

        # Create a dictionary to store average answer time per queue
        queue_avg_times = {}
        for row in result:
            queue_name = row[0]
            avg_seconds = float(row[1]) if row[1] is not None else 0  # Convert decimal to float
            avg_queue_answer_time = str(timedelta(seconds=avg_seconds))  # Convert to timedelta
            queue_avg_times[queue_name] = avg_queue_answer_time

        return queue_avg_times

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}

# Working with the cdr table.
def fetch_average_handle_time_for_queues(db: Session, user_time_zone: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text(""" 
        SELECT 
            cc_queue,
            AVG(
                (duration * INTERVAL '1 second') + (waitsec * INTERVAL '1 second') + (end_stamp - answer_stamp)
            ) AS avg_aht,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"queue": "N/A", "avg_time": 0, "avg_time_formatted": "00:00:00", "total_calls": 0}]

    avg_handle_times = []

    # If no results, return a default value for every queue
    if not results:
        return [{"queue": "N/A", "avg_time": 0, "avg_time_formatted": "00:00:00", "total_calls": 0}]

    for row in results:
        avg_aht = row[1] if row[1] is not None else timedelta(seconds=0)
        avg_aht_seconds = avg_aht.total_seconds()
        avg_aht_formatted = seconds_to_hms(int(avg_aht_seconds))

        avg_handle_times.append({
            "queue": row[0],  # cc_queue
            "avg_time": avg_aht_seconds,
            "avg_time_formatted": avg_aht_formatted,
            "total_calls": row[2]  # Total calls for the queue
        })

    return avg_handle_times

# Working with the cdr table. 
def fetch_contacts_handled_per_queue(db: Session, user_time_zone: str) -> Dict[str, int]:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled
        FROM cdr
        WHERE answer_stamp IS NOT NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Convert result to a dictionary (queue -> contacts_handled)
        queue_contacts_handled = {row[0]: row[1] for row in result if row[0] is not None}

        return queue_contacts_handled

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}

# Working with the cdr table.
def fetch_contacts_handled_incoming(db: Session, user_time_zone: str) -> Dict[str, int]:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled_incoming
        FROM cdr
        WHERE answer_stamp IS NOT NULL
        AND (
            direction = 'inbound'
            OR bleg_uuid IS NOT NULL -- Transferred contacts
        )
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Create a dictionary to store contacts handled incoming per queue
        contacts_handled_incoming_per_queue = {row[0]: row[1] for row in result if row[0] is not None}

        return contacts_handled_incoming_per_queue

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}  # Return an empty dictionary in case of error

# Working with the cdr table.
def fetch_contacts_queued(db: Session, user_time_zone: str) -> dict:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT cc_queue, COUNT(*) AS contacts_queued
        FROM cdr
        WHERE cc_queue IS NOT NULL
        AND end_stamp IS NOT NULL
        AND answer_stamp IS NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Create a dictionary to store contacts queued per queue and divide by 3
        queue_contacts_queued = {row[0]: row[1] // 3 for row in result}  # Dividing by 3

        return queue_contacts_queued

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}

# Working with the cdr table.
def fetch_contacts_abandoned(db: Session, user_time_zone: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT cc_queue, COUNT(*) AS abandoned_contacts
        FROM cdr
        WHERE answer_stamp IS NULL
        AND end_stamp IS NOT NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        abandoned_contacts = []
        for row in results:
            count = row[1]
            # Divide by 3 if count is greater than 0, else keep it 0
            abandoned_contacts.append({
                "queue": row[0],  # cc_queue
                "abandoned_count": count // 3 if count > 0 else 0  # Conditional check for 0
            })
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    return abandoned_contacts

# Working with the cdr table.
def fetch_contacts_handled_outbound(db: Session, user_time_zone: str) -> Dict[str, int]:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled_outbound
        FROM cdr
        WHERE direction = 'outbound'
        AND cc_queue IS NOT NULL
        AND start_stamp IS NOT NULL
        AND end_stamp IS NOT NULL
        AND answer_stamp IS NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Create a dictionary to store contacts handled outbound per queue
        contacts_handled_outbound_per_queue = {row[0]: row[1] for row in result if row[0] is not None}

        return contacts_handled_outbound_per_queue

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}  # Return an empty dictionary in case of error


# ---------------------------------------- 30 minutes time interval --------------------------------------------------->

# 30 minutes time intervals
# Working with the cdr table.
def fetch_unique_queue_names_for_30_minutes(db: Session, user_time_zone: str) -> list[str]:
    user_tz = pytz.timezone(user_time_zone)
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=30)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    print(f"Start Time (UTC): {start_time_utc}")
    print(f"End Time (UTC): {end_time_utc}")

    # Fetch distinct queue names from the 'cdr' table
    query = text("""
        SELECT DISTINCT cc_queue
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        })
        data = result.fetchall()
        print(f"Fetched {len(data)} unique queues from the database.")
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    if not data:
        print("No data found for the specified time range.")
        return []

    # Collect unique queue names
    queue_names = {row[0] for row in data}  # Using a set to ensure uniqueness

    print("Unique queue names:", queue_names)  # Check what names were added
    return list(queue_names)  # Convert set back to list if needed

# Working with the cdr table.
def fetch_service_level_60_seconds_per_queue_last_30_minutes(db: Session, user_time_zone: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=30)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT 
            cc_queue,
            FLOOR(SUM(CASE WHEN (answer_stamp - start_stamp) <= interval '60 seconds' THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(COUNT(*), 0)) AS service_level_60_seconds,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        print(f"Executing query with start_time: {start_time_utc}, end_time: {end_time_utc}")
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        print(f"Query results: {results}")
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"service_level_60_seconds": {"error": str(e)}}]

    service_levels = []
    
    for row in results:
        service_levels.append({
            "queue": row[0],  # cc_queue
            "service_level_60_seconds": f"{int(row[1])}%",  # Service level rounded down to nearest whole number
            "total_calls": row[2]  # Total calls for the queue
        })

    return service_levels

# Working with the cdr table.
def fetch_service_level_120_seconds_per_queue_last_30_minutes(db: Session, user_time_zone: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=30)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT 
            cc_queue,
            FLOOR(SUM(CASE WHEN (answer_stamp - start_stamp) <= interval '120 seconds' THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(COUNT(*), 0)) AS service_level_120_seconds,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return []  # Return an empty list on error

    service_levels = []
    
    for row in results:
        service_levels.append({
            "queue": row[0],  # cc_queue
            "service_level_120_seconds": f"{int(row[1])}%",  # Service level rounded down to nearest whole number
            "total_calls": row[2]  # Total calls for the queue
        })

    return service_levels if service_levels else []  # Return empty list if no data

# Working with the cdr table.
def fetch_average_after_contact_work_time_for_queues_last_30_minutes(db: Session, user_time_zone: str) -> list[dict]:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=30)

    # Convert the user's local times to UTC for querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT 
            cc_queue,
            SUM(COALESCE(end_stamp - answer_stamp, interval '0 seconds')) AS total_acw,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        # Execute the query with UTC timestamps
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"queue": None, "avg_time": 0, "avg_time_formatted": "00:00:00"}]

    avg_aacw_results = []

    for row in results:
        total_acw = row[1] if row[1] is not None else timedelta(seconds=0)
        total_calls = row[2] if row[2] is not None else 0

        # Calculate average ACW, handling division by zero
        if total_calls > 0:
            avg_acw_seconds = total_acw.total_seconds() / total_calls
        else:
            avg_acw_seconds = 0  # No calls, so average ACW is 0

        # Convert average seconds to HH:MM:SS format
        avg_acw_formatted = seconds_to_hms(int(avg_acw_seconds))

        avg_aacw_results.append({
            "queue": row[0],  # cc_queue
            "avg_time": avg_acw_seconds,
            "avg_time_formatted": avg_acw_formatted
        })

    return avg_aacw_results

# Working with the cdr table.
def fetch_average_agent_interaction_time_for_queues_last_30_minutes(db: Session, user_time_zone: str) -> list[dict]:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=30)

    # Convert the user's local times to UTC for querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    # Query to fetch the average agent interaction time and total calls per queue in the last 15 minutes
    query = text("""
        SELECT 
            cc_queue,
            SUM(EXTRACT(EPOCH FROM (end_stamp - answer_stamp))) AS total_interaction_time,  -- Sum of interaction time in seconds
            COUNT(*) AS total_calls  -- Total number of calls
        FROM cdr
        WHERE answer_stamp IS NOT NULL  -- Only consider answered calls
        AND timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL  -- Filter by non-null queues
        GROUP BY cc_queue
    """)

    try:
        # Execute the query with UTC timestamps
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"avg_time": 0, "avg_time_formatted": "00:00:00", "total_calls": 0}]

    avg_interaction_times = []

    # Loop through the results to calculate the average interaction time per queue
    for row in results:
        total_interaction_time = row[1]  # Total interaction time in seconds
        total_calls = row[2]  # Total number of calls

        # Calculate the average interaction time in seconds
        avg_interaction_seconds = total_interaction_time / total_calls if total_calls > 0 else 0

        # Convert the average time to HH:MM:SS format
        avg_interaction_formatted = seconds_to_hms(int(avg_interaction_seconds))

        avg_interaction_times.append({
            "queue": row[0],  # cc_queue
            "avg_time": avg_interaction_seconds,
            "avg_time_formatted": avg_interaction_formatted,
            "total_calls": total_calls
        })

    return avg_interaction_times

# Working with the cdr table. 
def fetch_average_queue_answer_time_per_queue_last_30_minutes(db: Session, user_time_zone: str) -> dict:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=30)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    # Print the time range being used for the query
    print(f"Querying data from {start_time_utc} to {end_time_utc}")

    query = text("""
        SELECT cc_queue, AVG(EXTRACT(EPOCH FROM (answer_stamp - start_stamp))) AS avg_queue_answer_time
        FROM cdr
        WHERE answer_stamp IS NOT NULL
        AND start_stamp IS NOT NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Print the raw result for debugging
        print(f"Raw result: {result}")

        # Create a dictionary to store average answer time per queue
        queue_avg_times = {}
        for row in result:
            queue_name = row[0]
            avg_seconds = float(row[1]) if row[1] is not None else 0  # Convert decimal to float
            avg_queue_answer_time = str(timedelta(seconds=avg_seconds))  # Convert to timedelta
            queue_avg_times[queue_name] = avg_queue_answer_time

        return queue_avg_times

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}

# Working with the cdr table.
def fetch_average_handle_time_for_queues_last_30_minutes(db: Session, user_time_zone: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=30)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text(""" 
        SELECT 
            cc_queue,
            AVG(
                (duration * INTERVAL '1 second') + (waitsec * INTERVAL '1 second') + (end_stamp - answer_stamp)
            ) AS avg_aht,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"queue": "N/A", "avg_time": 0, "avg_time_formatted": "00:00:00", "total_calls": 0}]

    avg_handle_times = []

    # If no results, return a default value for every queue
    if not results:
        return [{"queue": "N/A", "avg_time": 0, "avg_time_formatted": "00:00:00", "total_calls": 0}]

    for row in results:
        avg_aht = row[1] if row[1] is not None else timedelta(seconds=0)
        avg_aht_seconds = avg_aht.total_seconds()
        avg_aht_formatted = seconds_to_hms(int(avg_aht_seconds))

        avg_handle_times.append({
            "queue": row[0],  # cc_queue
            "avg_time": avg_aht_seconds,
            "avg_time_formatted": avg_aht_formatted,
            "total_calls": row[2]  # Total calls for the queue
        })

    return avg_handle_times

# Working with the cdr table. 
def fetch_contacts_handled_last_30_minutes_per_queue(db: Session, user_time_zone: str) -> Dict[str, int]:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=30)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled
        FROM cdr
        WHERE answer_stamp IS NOT NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
        
        # Convert result to a dictionary (queue -> contacts_handled)
        queue_contacts_handled = {row[0]: row[1] for row in result if row[0] is not None}

        return queue_contacts_handled

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}

# Working with the cdr table.
def fetch_contacts_handled_incoming_last_30_minutes(db: Session, user_time_zone: str) -> Dict[str, int]:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=30)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled_incoming
        FROM cdr
        WHERE answer_stamp IS NOT NULL
        AND (
            direction = 'inbound'
            OR bleg_uuid IS NOT NULL -- Transferred contacts
        )
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Create a dictionary to store contacts handled incoming per queue
        contacts_handled_incoming_per_queue = {row[0]: row[1] for row in result if row[0] is not None}

        return contacts_handled_incoming_per_queue

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}  # Return an empty dictionary in case of error

# Working with the cdr table.
def fetch_contacts_queued_last_30_minutes(db: Session, user_time_zone: str) -> dict:
    """
    Fetch the number of queued contacts for each queue in the last 30 minutes.
    """
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time in the user's time zone for logging/debugging purposes
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=30)

    # Convert to UTC for database querying (though we are using SQL's NOW() function directly in the query)
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    # Debugging logs to check calculated time ranges
    print(f"Fetching queued contacts from {start_time_utc} to {end_time_utc} (UTC) using timestamp column.")

    query = text("""
        SELECT cc_queue, COUNT(*) AS contacts_queued
        FROM cdr
        WHERE cc_queue IS NOT NULL
        AND end_stamp IS NOT NULL
        AND answer_stamp IS NULL
        AND timestamp >= (NOW() - INTERVAL '30 minutes')
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query).fetchall()

        # Log the raw query result for debugging
        print(f"Query results: {result}")

        # Create a dictionary to store contacts queued per queue and divide by 3
        queue_contacts_queued = {row[0]: row[1] // 3 for row in result}  # Dividing by 3

        # Log the final processed result
        print(f"Returned contacts queued data: {queue_contacts_queued}")

        return queue_contacts_queued

    except Exception as e:
        # Log any exception that occurs during the query
        print(f"Error executing query: {e}")
        return {}

# Working with the cdr table.
def fetch_contacts_abandoned_last_30_minutes(db: Session, user_time_zone: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=30)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT cc_queue, COUNT(*) AS abandoned_contacts
        FROM cdr
        WHERE answer_stamp IS NULL
        AND end_stamp IS NOT NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        abandoned_contacts = []
        for row in results:
            count = row[1]
            # Divide by 3 if count is greater than 0, else keep it 0
            abandoned_contacts.append({
                "queue": row[0],  # cc_queue
                "abandoned_count": count // 3 if count > 0 else 0  # Conditional check for 0
            })
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    return abandoned_contacts

# Working with the cdr table.
# def fetch_contacts_handled_outbound_last_30_minutes(db: Session, user_time_zone: str) -> Dict[str, int]:
#     user_tz = pytz.timezone(user_time_zone)

#     # Calculate the current time and start time in the user's time zone
#     now_user_time = datetime.now(user_tz)
#     start_time_user_time = now_user_time - timedelta(minutes=30)

#     # Convert to UTC for database querying
#     start_time_utc = start_time_user_time.astimezone(pytz.utc)
#     end_time_utc = now_user_time.astimezone(pytz.utc)

#     # query = text(""" 
#     #     SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled_outbound
#     #     FROM cdr
#     #     WHERE direction = 'outbound'
#     #     AND answer_stamp IS NULL
#     #     AND timestamp >= :start_time AND timestamp <= :end_time
#     #     GROUP BY cc_queue
#     # """)

#     query = text("""
#     SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled_outbound
#     FROM cdr
#     WHERE direction = 'outbound'
#     AND cc_queue IS NOT NULL
#     AND start_stamp IS NOT NULL
#     AND end_stamp IS NOT NULL
#     AND answer_stamp IS NULL
#     AND timestamp >= :start_time AND timestamp <= :end_time
#     GROUP BY cc_queue
# """)


#     try:
#         result = db.execute(query, {
#             'start_time': start_time_utc,
#             'end_time': end_time_utc
#         }).fetchall()

#         # Create a dictionary to store contacts handled outbound per queue
#         contacts_handled_outbound_per_queue = {row[0]: row[1] for row in result if row[0] is not None}

#         return contacts_handled_outbound_per_queue

#     except Exception as e:
#         print(f"Error executing query: {e}")
#         return {}  # Return an empty dictionary in case of error


def fetch_contacts_handled_outbound_last_30_minutes(db: Session, user_time_zone: str) -> Dict[str, int]:
    # Set up the user's timezone
    user_tz = pytz.timezone(user_time_zone)

    # Calculate current time and start time in the user's timezone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=30)

    # Convert the times to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    # Define the SQL query to count outbound contacts per queue
    query = text("""
        SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled_outbound
        FROM cdr
        WHERE direction = 'outbound'
        AND cc_queue IS NOT NULL
        AND start_stamp IS NOT NULL
        AND end_stamp IS NOT NULL
        AND answer_stamp IS NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        # Execute the query with start and end times as parameters
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Store contacts handled outbound per queue in a dictionary
        contacts_handled_outbound_per_queue = {row.cc_queue: row.contacts_handled_outbound for row in result if row.cc_queue is not None}

        return contacts_handled_outbound_per_queue

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}  # Return an empty dictionary in case of an error



# ------------------------------------  Today(since 12 am)  ---------------------------------------------------->

# today(since 12 AM interval)

# Working with the cdr table.
def fetch_unique_queue_names_for_today(db: Session, user_time_zone: str) -> list[str]:
    user_tz = pytz.timezone(user_time_zone)
    now_user_time = datetime.now(user_tz)
    
    # Get today's date and set time to 00:00:00 (12 AM)
    start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    print(f"Start Time (UTC): {start_time_utc}")
    print(f"End Time (UTC): {end_time_utc}")

    # Fetch distinct queue names from the 'cdr' table
    query = text("""
        SELECT DISTINCT cc_queue
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        })
        data = result.fetchall()
        print(f"Fetched {len(data)} unique queues from the database.")
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    if not data:
        print("No data found for the specified time range.")
        return []

    # Collect unique queue names
    queue_names = {row[0] for row in data}  # Using a set to ensure uniqueness

    print("Unique queue names:", queue_names)  # Check what names were added
    return list(queue_names)  # Convert set back to list if needed

# Working with the cdr table.
def fetch_service_level_60_seconds_per_queue_today(db: Session, user_time_zone: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)
    now_user_time = datetime.now(user_tz)

    # Get today's date and set time to 00:00:00 (12 AM)
    start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT 
            cc_queue,
            FLOOR(SUM(CASE WHEN (answer_stamp - start_stamp) <= interval '60 seconds' THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(COUNT(*), 0)) AS service_level_60_seconds,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        print(f"Executing query with start_time: {start_time_utc}, end_time: {end_time_utc}")
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        print(f"Query results: {results}")
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"service_level_60_seconds": {"error": str(e)}}]

    service_levels = []
    
    for row in results:
        service_levels.append({
            "queue": row[0],  # cc_queue
            "service_level_60_seconds": f"{int(row[1])}%",  # Service level as a whole number
            "total_calls": row[2]  # Total calls for the queue
        })

    return service_levels
 
# Working with the cdr table.
def fetch_service_level_120_seconds_per_queue_today(db: Session, user_time_zone: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)
    now_user_time = datetime.now(user_tz)

    # Get today's date and set time to 00:00:00 (12 AM)
    start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT 
            cc_queue,
            FLOOR(SUM(CASE WHEN (answer_stamp - start_stamp) <= interval '120 seconds' THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(COUNT(*), 0)) AS service_level_120_seconds,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return []  # Return an empty list on error

    service_levels = []
    
    for row in results:
        service_levels.append({
            "queue": row[0],  # cc_queue
            "service_level_120_seconds": f"{int(row[1])}%",  # Service level as a whole number
            "total_calls": row[2]  # Total calls for the queue
        })

    return service_levels if service_levels else []  # Return empty list if no data

# Working with the cdr table.
def fetch_average_after_contact_work_time_for_queues_today(db: Session, user_time_zone: str) -> list[dict]:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and set start time to today 00:00:00 (12 AM)
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert the user's local times to UTC for querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT 
            cc_queue,
            SUM(COALESCE(end_stamp - answer_stamp, interval '0 seconds')) AS total_acw,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        # Execute the query with UTC timestamps
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"queue": None, "avg_time": 0, "avg_time_formatted": "00:00:00"}]

    avg_acw_results = []

    for row in results:
        total_acw = row[1] if row[1] is not None else timedelta(seconds=0)
        total_calls = row[2] if row[2] is not None else 0

        # Calculate average ACW, handling division by zero
        if total_calls > 0:
            avg_acw_seconds = total_acw.total_seconds() / total_calls
        else:
            avg_acw_seconds = 0  # No calls, so average ACW is 0

        # Convert average seconds to HH:MM:SS format
        avg_acw_formatted = seconds_to_hms(int(avg_acw_seconds))

        avg_acw_results.append({
            "queue": row[0],  # cc_queue
            "avg_time": avg_acw_seconds,
            "avg_time_formatted": avg_acw_formatted
        })

    return avg_acw_results

# Working with the cdr table.
def fetch_average_agent_interaction_time_for_queues_today(db: Session, user_time_zone: str) -> list[dict]:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert the user's local times to UTC for querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    # Query to fetch the average agent interaction time and total calls per queue in the last 15 minutes
    query = text("""
        SELECT 
            cc_queue,
            SUM(EXTRACT(EPOCH FROM (end_stamp - answer_stamp))) AS total_interaction_time,  -- Sum of interaction time in seconds
            COUNT(*) AS total_calls  -- Total number of calls
        FROM cdr
        WHERE answer_stamp IS NOT NULL  -- Only consider answered calls
        AND timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL  -- Filter by non-null queues
        GROUP BY cc_queue
    """)

    try:
        # Execute the query with UTC timestamps
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"avg_time": 0, "avg_time_formatted": "00:00:00", "total_calls": 0}]

    avg_interaction_times = []

    # Loop through the results to calculate the average interaction time per queue
    for row in results:
        total_interaction_time = row[1]  # Total interaction time in seconds
        total_calls = row[2]  # Total number of calls

        # Calculate the average interaction time in seconds
        avg_interaction_seconds = total_interaction_time / total_calls if total_calls > 0 else 0

        # Convert the average time to HH:MM:SS format
        avg_interaction_formatted = seconds_to_hms(int(avg_interaction_seconds))

        avg_interaction_times.append({
            "queue": row[0],  # cc_queue
            "avg_time": avg_interaction_seconds,
            "avg_time_formatted": avg_interaction_formatted,
            "total_calls": total_calls
        })

    return avg_interaction_times

# Working with the cdr table.
def fetch_average_queue_answer_time_per_queue_today(db: Session, user_time_zone: str) -> dict:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and set start time to today 00:00:00 (12 AM)
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    # Print the time range being used for the query
    print(f"Querying data from {start_time_utc} to {end_time_utc}")

    query = text("""
        SELECT cc_queue, AVG(EXTRACT(EPOCH FROM (answer_stamp - start_stamp))) AS avg_queue_answer_time
        FROM cdr
        WHERE answer_stamp IS NOT NULL
        AND start_stamp IS NOT NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Print the raw result for debugging
        print(f"Raw result: {result}")

        # Create a dictionary to store average answer time per queue
        queue_avg_times = {}
        for row in result:
            queue_name = row[0]
            avg_seconds = float(row[1]) if row[1] is not None else 0  # Convert decimal to float
            avg_queue_answer_time = str(timedelta(seconds=avg_seconds))  # Convert to timedelta
            queue_avg_times[queue_name] = avg_queue_answer_time

        return queue_avg_times

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}

# Working with the cdr table.    
def fetch_average_handle_time_for_queues_today(db: Session, user_time_zone: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and set start time to today 00:00:00 (12 AM)
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text(""" 
        SELECT 
            cc_queue,
            AVG(
                (duration * INTERVAL '1 second') + (waitsec * INTERVAL '1 second') + (end_stamp - answer_stamp)
            ) AS avg_aht,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"queue": "N/A", "avg_time": 0, "avg_time_formatted": "00:00:00", "total_calls": 0}]

    avg_handle_times = []

    # If no results, return a default value for every queue
    if not results:
        return [{"queue": "N/A", "avg_time": 0, "avg_time_formatted": "00:00:00", "total_calls": 0}]

    for row in results:
        avg_aht = row[1] if row[1] is not None else timedelta(seconds=0)
        avg_aht_seconds = avg_aht.total_seconds()
        avg_aht_formatted = seconds_to_hms(int(avg_aht_seconds))

        avg_handle_times.append({
            "queue": row[0],  # cc_queue
            "avg_time": avg_aht_seconds,
            "avg_time_formatted": avg_aht_formatted,
            "total_calls": row[2]  # Total calls for the queue
        })

    return avg_handle_times

# Working with the cdr table.
def fetch_contacts_handled_today(db: Session, user_time_zone: str) -> Dict[str, int]:
    user_tz = pytz.timezone(user_time_zone)

    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled
        FROM cdr
        WHERE answer_stamp IS NOT NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Logging the result for debugging
        print("Query Result for contacts handled today:", result)

        # Create a dictionary to store contacts handled per queue,
        # filtering out any rows where cc_queue is None
        contacts_handled_per_queue = {row[0]: row[1] for row in result if row[0] is not None}

        # Return the dictionary (this should never be None)
        return contacts_handled_per_queue

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}


# Working with the cdr table.
def fetch_contacts_handled_incoming_today(db: Session, user_time_zone: str) -> Dict[str, int]:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and set start time to today 00:00:00 (12 AM)
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text(""" 
        SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled_incoming
        FROM cdr
        WHERE answer_stamp IS NOT NULL
        AND (
            direction = 'inbound'
            OR bleg_uuid IS NOT NULL -- Transferred contacts
        )
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Create a dictionary to store contacts handled incoming per queue
        contacts_handled_incoming_per_queue = {row[0]: row[1] for row in result if row[0] is not None}

        return contacts_handled_incoming_per_queue

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}  # Return an empty dictionary in case of error


# Working with the cdr table.
def fetch_contacts_queued_today(db: Session, user_time_zone: str) -> dict:
    """
    Fetch the number of queued contacts for each queue for the current day (from 12:00 AM today to now).
    """
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and set start time to today 00:00:00 (12 AM) in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert to UTC for database querying (though SQL's 'current_date' could handle this directly)
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    # Debugging logs to check time ranges
    print(f"Fetching queued contacts from {start_time_utc} (UTC) to {end_time_utc} (UTC).")

    query = text("""
        SELECT cc_queue, COUNT(*) AS contacts_queued
        FROM cdr
        WHERE cc_queue IS NOT NULL
        AND end_stamp IS NOT NULL
        AND answer_stamp IS NULL
        AND timestamp >= CURRENT_DATE
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query).fetchall()

        # Log the raw query result for debugging
        print(f"Query results: {result}")

        # Create a dictionary to store contacts queued per queue and divide by 3
        queue_contacts_queued = {row[0]: row[1] // 3 for row in result}  # Dividing by 3

        # Log the final processed result
        print(f"Returned contacts queued data: {queue_contacts_queued}")

        return queue_contacts_queued

    except Exception as e:
        # Log any exception that occurs during the query
        print(f"Error executing query: {e}")
        return {}

# Working with the cdr table.
def fetch_contacts_abandoned_today(db: Session, user_time_zone: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and set start time to today 00:00:00 (12 AM)
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text(""" 
        SELECT cc_queue, COUNT(*) AS abandoned_contacts
        FROM cdr
        WHERE answer_stamp IS NULL
        AND end_stamp IS NOT NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        abandoned_contacts = []
        for row in results:
            count = row[1]
            # Divide by 3 if count is greater than 0, else keep it 0
            abandoned_contacts.append({
                "queue": row[0],  # cc_queue
                "abandoned_count": count // 3 if count > 0 else 0  # Conditional check for 0
            })
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    return abandoned_contacts


# Working with the cdr table.
# def fetch_contacts_handled_outbound_today(db: Session, user_time_zone: str) -> Dict[str, int]:
#     user_tz = pytz.timezone(user_time_zone)

#     # Calculate the current time and set start time to today 00:00:00 (12 AM)
#     now_user_time = datetime.now(user_tz)
#     start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)

#     # Convert to UTC for database querying
#     start_time_utc = start_time_user_time.astimezone(pytz.utc)
#     end_time_utc = now_user_time.astimezone(pytz.utc)

#     # query = text(""" 
#     #     SELECT COUNT(DISTINCT uuid) AS contacts_handled_outbound
#     #     FROM cdr
#     #     WHERE direction = 'outbound'
#     #     AND answer_stamp IS NOT NULL
#     #     AND timestamp >= :start_time AND timestamp <= :end_time
#     # """)

#     query = text("""
#         SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled_outbound
#         FROM cdr
#         WHERE direction = 'outbound'
#         AND cc_queue IS NOT NULL
#         AND start_stamp IS NOT NULL
#         AND end_stamp IS NOT NULL
#         AND answer_stamp IS NULL
#         AND timestamp >= :start_time AND timestamp <= :end_time
#         GROUP BY cc_queue
#     """)

#     try:
#         result = db.execute(query, {
#             'start_time': start_time_utc,
#             'end_time': end_time_utc
#         }).fetchone()
        
#         contacts_handled_outbound = result[0] if result[0] is not None else 0

#         # Return a dictionary with the appropriate format
#         return {'total': contacts_handled_outbound}

#     except Exception as e:
#         print(f"Error executing query: {e}")
#         return {'total': 0}  # In case of an error, return a dictionary with 'total' set to 0


def fetch_contacts_handled_outbound_today(db: Session, user_time_zone: str) -> Dict[str, int]:
    user_tz = pytz.timezone(user_time_zone)
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled_outbound
        FROM cdr
        WHERE direction = 'outbound'
        AND cc_queue IS NOT NULL
        AND start_stamp IS NOT NULL
        AND end_stamp IS NOT NULL
        AND answer_stamp IS NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
        
        # Create a dictionary with queue names and counts
        contacts_handled_outbound_per_queue = {row.cc_queue: row.contacts_handled_outbound for row in result}

        return contacts_handled_outbound_per_queue

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}


# ------------------------------------------   custom date range  ---------------------------------------------->

# date range metric 
# Working with the cdr table.
def fetch_unique_queue_names_for_date_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> list[str]:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    print(f"Start Time (UTC): {start_time_utc}")
    print(f"End Time (UTC): {end_time_utc}")

    # Fetch distinct queue names from the 'cdr' table
    query = text("""
        SELECT DISTINCT cc_queue
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        })
        data = result.fetchall()
        print(f"Fetched {len(data)} unique queues from the database.")
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    if not data:
        print("No data found for the specified time range.")
        return []

    # Collect unique queue names
    queue_names = {row[0] for row in data}  # Using a set to ensure uniqueness

    print("Unique queue names:", queue_names)  # Check what names were added
    return list(queue_names)  # Convert set back to list if needed


# Working with the cdr table.
def fetch_service_level_60_seconds_per_queue_for_date_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz).replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT 
            cc_queue,
            FLOOR(SUM(CASE WHEN (answer_stamp - start_stamp) <= interval '60 seconds' THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(COUNT(*), 0)) AS service_level_60_seconds,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        print(f"Executing query with start_time: {start_time_utc}, end_time: {end_time_utc}")
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        print(f"Query results: {results}")
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"service_level_60_seconds": {"error": str(e)}}]

    service_levels = []
    
    for row in results:
        service_levels.append({
            "queue": row[0],  # cc_queue
            "service_level_60_seconds": f"{int(row[1])}%",  # Service level as a whole number
            "total_calls": row[2]  # Total calls for the queue
        })

    return service_levels


# Working with the cdr table.
def fetch_service_level_120_seconds_per_queue_for_date_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz).replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT 
            cc_queue,
            FLOOR(SUM(CASE WHEN (answer_stamp - start_stamp) <= interval '120 seconds' THEN 1 ELSE 0 END) * 100.0 / 
            NULLIF(COUNT(*), 0)) AS service_level_120_seconds,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return []  # Return an empty list on error

    service_levels = []
    
    for row in results:
        service_levels.append({
            "queue": row[0],  # cc_queue
            "service_level_120_seconds": f"{int(row[1])}%",  # Service level as a whole number
            "total_calls": row[2]  # Total calls for the queue
        })

    return service_levels if service_levels else []  # Return empty list if no data

# Working with the cdr table.
def fetch_average_after_contact_work_time_for_queues_for_date_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> list[dict]:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz).replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT 
            cc_queue,
            SUM(COALESCE(end_stamp - answer_stamp, interval '0 seconds')) AS total_acw,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        # Execute the query with UTC timestamps
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"queue": None, "avg_time": 0, "avg_time_formatted": "00:00:00"}]

    avg_acw_results = []

    for row in results:
        total_acw = row[1] if row[1] is not None else timedelta(seconds=0)
        total_calls = row[2] if row[2] is not None else 0

        # Calculate average ACW, handling division by zero
        if total_calls > 0:
            avg_acw_seconds = total_acw.total_seconds() / total_calls
        else:
            avg_acw_seconds = 0  # No calls, so average ACW is 0

        # Convert average seconds to HH:MM:SS format
        avg_acw_formatted = seconds_to_hms(int(avg_acw_seconds))

        avg_acw_results.append({
            "queue": row[0],  # cc_queue
            "avg_time": avg_acw_seconds,
            "avg_time_formatted": avg_acw_formatted
        })

    return avg_acw_results


# Working with the cdr table.
def fetch_average_agent_interaction_time_for_queues_for_date_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> list[dict]:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz).replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    # Query to fetch the average agent interaction time and total calls per queue in the specified date range
    query = text("""
        SELECT 
            cc_queue,
            SUM(EXTRACT(EPOCH FROM (end_stamp - answer_stamp))) AS total_interaction_time,  -- Sum of interaction time in seconds
            COUNT(*) AS total_calls  -- Total number of calls
        FROM cdr
        WHERE answer_stamp IS NOT NULL  -- Only consider answered calls
        AND timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL  -- Filter by non-null queues
        GROUP BY cc_queue
    """)

    try:
        # Execute the query with UTC timestamps
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"avg_time": 0, "avg_time_formatted": "00:00:00", "total_calls": 0}]

    avg_interaction_times = []

    # Loop through the results to calculate the average interaction time per queue
    for row in results:
        total_interaction_time = row[1]  # Total interaction time in seconds
        total_calls = row[2]  # Total number of calls

        # Calculate the average interaction time in seconds
        avg_interaction_seconds = total_interaction_time / total_calls if total_calls > 0 else 0

        # Convert the average time to HH:MM:SS format
        avg_interaction_formatted = seconds_to_hms(int(avg_interaction_seconds))

        avg_interaction_times.append({
            "queue": row[0],  # cc_queue
            "avg_time": avg_interaction_seconds,
            "avg_time_formatted": avg_interaction_formatted,
            "total_calls": total_calls
        })

    return avg_interaction_times


# Working with the cdr table.
def fetch_average_queue_answer_time_per_queue_for_date_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> dict:
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz).replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    # Print the time range being used for the query
    print(f"Querying data from {start_time_utc} to {end_time_utc}")

    query = text("""
        SELECT cc_queue, AVG(EXTRACT(EPOCH FROM (answer_stamp - start_stamp))) AS avg_queue_answer_time
        FROM cdr
        WHERE answer_stamp IS NOT NULL
        AND start_stamp IS NOT NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Print the raw result for debugging
        print(f"Raw result: {result}")

        # Create a dictionary to store average answer time per queue
        queue_avg_times = {}
        for row in result:
            queue_name = row[0]
            avg_seconds = float(row[1]) if row[1] is not None else 0  # Convert decimal to float
            avg_queue_answer_time = str(timedelta(seconds=avg_seconds))  # Convert to timedelta
            queue_avg_times[queue_name] = avg_queue_answer_time

        return queue_avg_times

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}


# Working with the cdr table.
def fetch_average_handle_time_for_queues_for_date_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz).replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    query = text(""" 
        SELECT 
            cc_queue,
            AVG(
                (duration * INTERVAL '1 second') + (waitsec * INTERVAL '1 second') + (end_stamp - answer_stamp)
            ) AS avg_aht,
            COUNT(*) AS total_calls
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return [{"queue": "N/A", "avg_time": 0, "avg_time_formatted": "00:00:00", "total_calls": 0}]

    avg_handle_times = []

    # If no results, return a default value for every queue
    if not results:
        return [{"queue": "N/A", "avg_time": 0, "avg_time_formatted": "00:00:00", "total_calls": 0}]

    for row in results:
        avg_aht = row[1] if row[1] is not None else timedelta(seconds=0)
        avg_aht_seconds = avg_aht.total_seconds()
        avg_aht_formatted = seconds_to_hms(int(avg_aht_seconds))

        avg_handle_times.append({
            "queue": row[0],  # cc_queue
            "avg_time": avg_aht_seconds,
            "avg_time_formatted": avg_aht_formatted,
            "total_calls": row[2]  # Total calls for the queue
        })

    return avg_handle_times


# Working with the cdr table.
def fetch_contacts_handled_for_date_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> Dict[str, int]:
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz).replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled
        FROM cdr
        WHERE answer_stamp IS NOT NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Create a dictionary to store contacts handled per queue
        contacts_handled_per_queue = {row[0]: row[1] for row in result if row[0] is not None}

        return contacts_handled_per_queue

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}


# Working with the cdr table.
def fetch_contacts_handled_incoming_for_date_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> Dict[str, int]:
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz).replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    query = text(""" 
        SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled_incoming
        FROM cdr
        WHERE answer_stamp IS NOT NULL
        AND (
            direction = 'inbound'
            OR bleg_uuid IS NOT NULL -- Transferred contacts
        )
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Create a dictionary to store contacts handled incoming per queue
        contacts_handled_incoming_per_queue = {row[0]: row[1] for row in result if row[0] is not None}

        return contacts_handled_incoming_per_queue

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}  # Return an empty dictionary in case of error


# Working with the cdr table.
def fetch_contacts_queued_for_date_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> dict:
    """
    Fetch the number of queued contacts for each queue within the specified date range.
    """
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz).replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    # Debugging logs to check time ranges
    print(f"Fetching queued contacts from {start_time_utc} (UTC) to {end_time_utc} (UTC).")

    query = text(""" 
        SELECT cc_queue, COUNT(*) AS contacts_queued
        FROM cdr
        WHERE cc_queue IS NOT NULL
        AND end_stamp IS NOT NULL
        AND answer_stamp IS NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Log the raw query result for debugging
        print(f"Query results: {result}")

        # Create a dictionary to store contacts queued per queue and divide by 3
        queue_contacts_queued = {row[0]: row[1] // 3 for row in result}  # Dividing by 3

        # Log the final processed result
        print(f"Returned contacts queued data: {queue_contacts_queued}")

        return queue_contacts_queued

    except Exception as e:
        # Log any exception that occurs during the query
        print(f"Error executing query: {e}")
        return {}


# Working with the cdr table.
def fetch_contacts_abandoned_for_date_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> list[dict]:
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz).replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    query = text(""" 
        SELECT cc_queue, COUNT(*) AS abandoned_contacts
        FROM cdr
        WHERE answer_stamp IS NULL
        AND end_stamp IS NOT NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        AND cc_queue IS NOT NULL
        GROUP BY cc_queue
    """)

    try:
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        abandoned_contacts = []
        for row in results:
            count = row[1]
            # Divide by 3 if count is greater than 0, else keep it 0
            abandoned_contacts.append({
                "queue": row[0],  # cc_queue
                "abandoned_count": count // 3 if count > 0 else 0  # Conditional check for 0
            })

    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    return abandoned_contacts


# Working with the cdr table.
def fetch_contacts_handled_outbound_for_date_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> Dict[str, int]:
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz).replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    # query = text(""" 
    #     SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled_outbound
    #     FROM cdr
    #     WHERE direction = 'outbound'
    #     AND answer_stamp IS NULL
    #     AND timestamp >= :start_time AND timestamp <= :end_time
    #     GROUP BY cc_queue
    # """)

    query = text("""
        SELECT cc_queue, COUNT(DISTINCT uuid) AS contacts_handled_outbound
        FROM cdr
        WHERE direction = 'outbound'
        AND cc_queue IS NOT NULL
        AND start_stamp IS NOT NULL
        AND end_stamp IS NOT NULL
        AND answer_stamp IS NULL
        AND timestamp >= :start_time AND timestamp <= :end_time
        GROUP BY cc_queue
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Create a dictionary to store contacts handled outbound per queue
        contacts_handled_outbound_per_queue = {row[0]: row[1] for row in result if row[0] is not None}

        return contacts_handled_outbound_per_queue

    except Exception as e:
        print(f"Error executing query: {e}")
        return {}  # Return an empty dictionary in case of error







