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


# ----------------------------------------- login/logout ------------------------------>

# Working with the login_logout table.
def fetch_agent_login_logout_today(db: Session, user_time_zone: str) -> list:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Get the current time in the user's timezone
    now_user_time = datetime.now(user_tz)
    
    # Get the start of today (12 AM) in the user's timezone
    start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert the user's local times to UTC for querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    now_utc = now_user_time.astimezone(pytz.utc)

    # SQL query to get the agent's login/logout details for today where both login and logout timestamps exist
    query = text("""
        SELECT
            agent_name,
            login_timestamp,
            logout_timestamp,
            duration
        FROM
            login_logout
        WHERE
            timestamp >= :start_time
            AND timestamp <= :end_time
            AND role = 'Agent'
            AND login_timestamp IS NOT NULL
            AND logout_timestamp IS NOT NULL
        ORDER BY
            agent_name, login_timestamp;
    """)

    try:
        # Execute the query with UTC timestamps
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': now_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    # Process the results into schema objects
    return [
        {
            'agent_name': row[0],  # Access by tuple index
            'login_timestamp': row[1],  # Access by tuple index
            'logout_timestamp': row[2],  # Access by tuple index
            'duration': row[3]  # Access by tuple index
        }
        for row in results
    ]


# Working with the cdr table.
def fetch_agent_login_logout_for_date_range(db: Session, user_time_zone: str,
                                            start_date: str, end_date: str) -> list:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz)

    # Convert the user's local times to UTC for querying the database
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    # SQL query to get the agent's login/logout details for the custom date range
    query = text("""
        SELECT
            agent_name,
            login_timestamp,
            logout_timestamp,
            duration
        FROM
            login_logout
        WHERE
            timestamp >= :start_time
            AND timestamp <= :end_time
            AND role = 'Agent'
            AND login_timestamp IS NOT NULL
            AND logout_timestamp IS NOT NULL
        ORDER BY
            agent_name, login_timestamp;
    """)

    try:
        # Execute the query with UTC timestamps
        results = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    # Process the results into schema objects
    return [
        {
            'agent_name': row[0],  # Access by tuple index
            'login_timestamp': row[1],  # Access by tuple index
            'logout_timestamp': row[2],  # Access by tuple index
            'duration': row[3]  # Access by tuple index
        }
        for row in results
    ]