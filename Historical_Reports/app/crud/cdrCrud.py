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


# ------------------------------------------ CDR Reports ----------------------------------->

def fetch_cdr_today(db: Session, user_time_zone: str) -> list:
    user_tz = pytz.timezone(user_time_zone)
    now_user_time = datetime.now(user_tz)
    start_time_user = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)

    start_utc = start_time_user.astimezone(pytz.utc)
    end_utc = now_user_time.astimezone(pytz.utc)

    query = text("""
        SELECT
            cc_agent,
            cc_queue,
            destination_number,
            caller_id_number,
            uuid,
            answer_stamp,
            direction,
            duration,
            start_stamp,
            end_stamp,
            billsec
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        ORDER BY start_stamp DESC
    """)

    try:
        results = db.execute(query, {'start_time': start_utc, 'end_time': end_utc}).fetchall()
    except Exception as e:
        print(f"Error fetching CDR today: {e}")
        return []

    return [
        {
            'name': row[0],
            'queue': row[1],
            'destination_number': row[2],
            'caller_id': row[3],
            'uuid': str(row[4]),  # ✅ Cast UUID to string
            'answer_time': row[5],
            'direction': row[6],
            'duration': row[7],
            'start_time': row[8],
            'end_time': row[9],
            'billsec': row[10]
        }
        for row in results
    ]


def fetch_cdr_custom_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> list:
    user_tz = pytz.timezone(user_time_zone)
    start_user = datetime.fromisoformat(start_date).astimezone(user_tz)
    end_user = datetime.fromisoformat(end_date).astimezone(user_tz)

    start_utc = start_user.astimezone(pytz.utc)
    end_utc = end_user.astimezone(pytz.utc)

    query = text("""
        SELECT
            cc_agent,
            cc_queue,
            destination_number,
            caller_id_number,
            uuid,
            answer_stamp,
            direction,
            duration,
            start_stamp,
            end_stamp,
            billsec
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
        ORDER BY start_stamp DESC
    """)

    try:
        results = db.execute(query, {'start_time': start_utc, 'end_time': end_utc}).fetchall()
    except Exception as e:
        print(f"Error fetching CDR custom range: {e}")
        return []

    return [
        {
            'name': row[0],
            'queue': row[1],
            'destination_number': row[2],
            'caller_id': row[3],
            'uuid': str(row[4]),  # ✅ Cast UUID to string
            'answer_time': row[5],
            'direction': row[6],
            'duration': row[7],
            'start_time': row[8],
            'end_time': row[9],
            'billsec': row[10]
        }
        for row in results
    ]