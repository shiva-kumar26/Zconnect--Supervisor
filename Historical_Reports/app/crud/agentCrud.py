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


#-------------------------------- metrics for 15 minutes time interval ---------------------->

# Working with the cdr table. 
def get_recent_agent_names_last_15_minutes(db: Session, user_time_zone: str) -> list[str]:
    user_tz = pytz.timezone(user_time_zone)
    default_tz = pytz.utc
    now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
    start_time_utc = now_utc - timedelta(minutes=15)

    print(f"Start Time (UTC): {start_time_utc}")
    print(f"End Time (UTC): {now_utc}")

    query = text("""
        SELECT DISTINCT cc_agent
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
          AND cc_agent IS NOT NULL
    """)
    
    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': now_utc
        })
        data = result.fetchall()
        print(f"Fetched {len(data)} records from the database.")
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    if not data:
        print("No data found for the specified time range.")

    agent_names = [row[0] for row in data]  # Get the agent names from the fetched data

    print("Agent names:", agent_names)  # Check what names were added
    return agent_names

# Working with the cdr table.
def fetch_agent_answer_rate_last_15_minutes(db: Session, user_time_zone: str) -> list:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=15)

    # Convert the user's local times to UTC for querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    # SQL query to calculate the answer rate based on the `timestamp` column
    query = text("""  
        WITH agent_call_data AS (
            SELECT
                cc_agent AS agent_name,
                COUNT(CASE WHEN answer_stamp IS NOT NULL AND billsec > 0 THEN 1 END) AS calls_answered,
                COUNT(CASE WHEN answer_stamp IS NULL OR billsec = 0 THEN 1 END) AS no_answer_count
            FROM cdr
            WHERE timestamp >= :start_time
            AND timestamp <= :end_time
            AND cc_agent IS NOT NULL  -- Filter out records without an agent
            GROUP BY cc_agent
        )
        SELECT
            agent_name,
            ROUND(
                (SUM(calls_answered) * 100.0 / 
                 CASE
                    WHEN (SUM(no_answer_count) + SUM(calls_answered)) = 0 THEN 1
                    ELSE (SUM(no_answer_count) + SUM(calls_answered))
                 END
                )
            ) AS agent_answer_rate
        FROM agent_call_data
        GROUP BY agent_name;
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

    return results

# Working with the cdr table.
def fetch_agent_non_response_last_15_minutes(
        db: Session, user_time_zone: str) -> List[schemas.AgentNonResponse]:
    # Convert the user's timezone to UTC for querying
    user_tz = pytz.timezone(user_time_zone)
    now_user = datetime.now(user_tz)

    # Calculate the start time as 15 minutes before the current time in the user's time zone
    start_time_user = now_user - timedelta(minutes=15)

    # Convert to UTC for the query
    start_time_utc = start_time_user.astimezone(pytz.utc)
    now_utc = now_user.astimezone(pytz.utc)

    # SQL query to sum non-answered calls for each agent in the last 15 minutes
    query = text("""  
        SELECT
            cc_agent AS name,
            COUNT(*) AS no_answer_count
        FROM
            cdr
        WHERE
            timestamp >= :start_time AND
            timestamp <= :end_time AND
            answer_stamp IS NULL
        GROUP BY
            cc_agent;
    """)

    # Execute the query
    result = db.execute(query, {'start_time': start_time_utc, 'end_time': now_utc}).fetchall()

    # Process the data, ensuring no None values for name, and divide the count by 3
    processed_result = [
        schemas.AgentNonResponse( 
            name=row[0],  # Agent name
            no_answer_count=(row[1] // 3) if row[1] is not None else 0  # Count of non-responses divided by 3
        ) for row in result if row[0] is not None  # Filter out None names
    ]

    # Ensure all agents are represented, even if they have 0 non-responses
    if not processed_result:
        return [schemas.AgentNonResponse(name="No Agents", no_answer_count=0)]

    return processed_result

# Working with the cdr table..
def fetch_agent_contacts_handled_last_15_minutes(db: Session, user_time_zone: str) -> List[Dict[str, str]]:
    try:
        # Convert the user's timezone to UTC for querying
        user_tz = pytz.timezone(user_time_zone)

        # Get current time in user's time zone and convert it to UTC
        now_user = datetime.now(user_tz)
        start_time_user = now_user - timedelta(minutes=15)
        start_time_utc = start_time_user.astimezone(pytz.utc)

        # SQL query to track and sum the count of answered calls for each agent in the last 15 minutes from the cdr table
        query = text("""
            SELECT 
                cc_agent AS name, 
                COUNT(answer_stamp) AS total_calls_answered
            FROM 
                cdr
            WHERE 
                timestamp >= :start_time
                AND answer_stamp IS NOT NULL
                AND cc_agent IS NOT NULL
            GROUP BY 
                cc_agent
        """)

        # Execute the SQL query using UTC for querying
        result = db.execute(query, {
            'start_time': start_time_utc
        }).fetchall()

        # Format the results, ensuring "0" is returned when the count is zero
        formatted_result = [
            {
                "name": row[0],  # Access tuple elements by index
                "contacts_handled": row[1]  # Directly use the integer result
            } for row in result
        ]

        # Handle case where no agents are returned
        if not formatted_result:
            return [{"name": "No Agents", "contacts_handled": 0}]  # Return a default entry

        return formatted_result

    except Exception as e:
        print(f"Error executing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Working with the cdr table..
def fetch_agent_on_contact_time_last_15_minutes(db: Session, user_time_zone: str) -> list:
    # Convert the user's timezone to UTC for querying
    user_tz = pytz.timezone(user_time_zone)
    now_user = datetime.now(user_tz)
    start_time_user = now_user - timedelta(minutes=15)

    # Convert user's time to UTC for querying
    start_time_utc = start_time_user.astimezone(pytz.utc)
    now_utc = now_user.astimezone(pytz.utc)

    # Query to fetch all relevant data within the time frame from the CDR table
    query = text("""
        SELECT 
            cc_agent, 
            end_stamp, 
            answer_stamp,
            timestamp
        FROM 
            cdr
        WHERE 
            timestamp >= :start_time 
            AND timestamp <= :end_time
        ORDER BY timestamp
    """)

    # Execute the query
    result = db.execute(query, {
        'start_time': start_time_utc,
        'end_time': now_utc
    }).fetchall()

    formatted_result = []
    total_contact_time = {}  # Dictionary to store total contact time per agent

    for row in result:
        agent_name = row[0]  # cc_agent
        end_stamp = row[1]   # end_stamp
        answer_stamp = row[2] # answer_stamp
        call_timestamp = row[3]  # timestamp

        # Ensure that we only process records with a valid agent name and non-null stamps
        if agent_name and end_stamp and answer_stamp:
            # Calculate the contact duration as the difference between end_stamp and answer_stamp
            contact_duration = (end_stamp - answer_stamp).total_seconds()

            # Convert call's timestamp to the user's local time for comparison
            call_timestamp_local = call_timestamp.astimezone(user_tz)

            # Check if the call falls within the last 15 minutes in the user's local time
            if start_time_user <= call_timestamp_local <= now_user:
                # Accumulate contact time for each agent
                if agent_name not in total_contact_time:
                    total_contact_time[agent_name] = 0  # Initialize if not already in dict
                total_contact_time[agent_name] += contact_duration  # Sum up the durations

    # Format the results for output
    for agent_name, total_seconds in total_contact_time.items():
        # Convert total seconds to timedelta for formatting
        delta = timedelta(seconds=total_seconds)
        formatted_time = str(delta).split()[-1]  # Get the time part

        formatted_result.append({
            "name": agent_name,
            "total_on_contact_time_seconds": formatted_time  # Format total time as a string
        })

    return formatted_result

# working with historical agent's table.
def fetch_agent_online_time_last_15_minutes(db: Session, user_time_zone: str) -> List[schemas.AgentOnlineTime]:
    try:
        # Convert the user's timezone to UTC for querying
        user_tz = pytz.timezone(user_time_zone)
        now_user = datetime.now(user_tz)
        start_time_user = now_user - timedelta(minutes=15)

        # Convert user's local times to UTC for querying
        start_time_utc = start_time_user.astimezone(pytz.utc)
        now_utc = now_user.astimezone(pytz.utc)  # Current UTC time

        # SQL query to calculate online time for each "Available" period
        query = text("""
            WITH available_periods AS (
                SELECT 
                    name,
                    timestamp AS available_timestamp,
                    LEAD(timestamp) OVER (PARTITION BY name ORDER BY timestamp) AS next_timestamp,
                    status
                FROM historical_agents_metrics
                WHERE timestamp >= :start_time AND timestamp <= :end_time
                ORDER BY name, timestamp
            )
            SELECT 
                name,
                SUM(EXTRACT(EPOCH FROM (COALESCE(next_timestamp, now()) - available_timestamp))) AS online_time
            FROM available_periods
            WHERE status = 'Available'
            GROUP BY name;
        """)

        # Fetch the results from the database
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': now_utc
        }).fetchall()

        # Format results
        formatted_result = []
        for row in result:
            name, total_online_time = row
            # Convert total_online_time to HH:MM:SS without microseconds
            formatted_result.append({
                "name": name,
                "online_time": seconds_to_hms(int(total_online_time))  # Ensure only seconds are used
            })

        return formatted_result
    except Exception as e:
        print(f"Error in fetch_agent_online_time_last_15_minutes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# working from the historical agent's table
def fetch_non_productive_time_last_15_minutes(db: Session, user_time_zone: str) -> list:
    try:
        # Convert the user's timezone to UTC
        user_tz = pytz.timezone(user_time_zone)
        now_user = datetime.now(user_tz)
        start_time_user = now_user - timedelta(minutes=15)

        # Convert to UTC
        start_time_utc = start_time_user.astimezone(pytz.utc)
        now_utc = now_user.astimezone(pytz.utc)

        # SQL query to fetch all status records (including "On break" statuses)
        query = text("""
            WITH status_changes AS (
                SELECT 
                    ham.name,
                    ham.status,
                    ham.timestamp,
                    LEAD(ham.status) OVER (PARTITION BY ham.name ORDER BY ham.timestamp) AS next_status,
                    LEAD(ham.timestamp) OVER (PARTITION BY ham.name ORDER BY ham.timestamp) AS next_timestamp
                FROM historical_agents_metrics ham
                WHERE ham.timestamp >= :start_time 
                  AND ham.timestamp <= :end_time
            )
            SELECT 
                csp.name,
                csp.status,
                csp.timestamp,
                csp.next_status,
                csp.next_timestamp
            FROM status_changes csp
            WHERE csp.status = 'On Break'
              AND csp.next_status != 'On Break';
        """)

        # Fetch results from the database
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': now_utc
        }).fetchall()

        # Calculate the non-productive time for each agent
        formatted_result = []
        for row in result:
            name, status, on_break_timestamp, next_status, next_timestamp = row

            # Calculate non-productive time in seconds
            non_productive_time_seconds = (next_timestamp - on_break_timestamp).total_seconds()

            # Convert seconds to HH:MM:SS format
            formatted_result.append({
                "name": name,
                "non_productive_time_seconds": seconds_to_hms(int(non_productive_time_seconds)) if non_productive_time_seconds else "00:00:00"
            })

        # Group results by agent and sum non-productive times
        agent_times = {}
        for entry in formatted_result:
            name = entry["name"]
            if name in agent_times:
                # Sum non-productive times for the same agent
                current_time = agent_times[name]
                agent_times[name] = seconds_to_hms(int(current_time.split(":")[0]) * 3600 + int(current_time.split(":")[1]) * 60 + int(current_time.split(":")[2]) + int(entry["non_productive_time_seconds"].split(":")[2]))
            else:
                agent_times[name] = entry["non_productive_time_seconds"]

        # Return the result in the desired format
        return [{"name": name, "non_productive_time_seconds": time} for name, time in agent_times.items()]

    except Exception as e:
        print(f"Error in fetch_non_productive_time_last_15_minutes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Working with the cdr table.
def fetch_average_after_contact_work_time_last_15_minutes(
        db: Session, user_time_zone: str) -> List[Dict[str, any]]:
    try:
        # Convert the user's timezone to UTC for querying
        user_tz = pytz.timezone(user_time_zone)
        now_user = datetime.now(user_tz)
        start_time_user = now_user - timedelta(minutes=15)

        # Convert user's time to UTC for querying
        start_time_utc = start_time_user.astimezone(pytz.utc)
        now_utc = now_user.astimezone(pytz.utc)

        # SQL query to fetch answer_stamp and end_stamp from cdr table
        query = text("""
            SELECT 
                cc_agent,
                SUM(EXTRACT(EPOCH FROM (end_stamp - answer_stamp))) AS total_acw_duration,
                COUNT(*) AS total_contacts
            FROM 
                cdr
            WHERE 
                timestamp >= :start_time 
                AND timestamp <= :end_time 
                AND end_stamp IS NOT NULL
                AND answer_stamp IS NOT NULL
            GROUP BY 
                cc_agent
        """)

        # Execute the query
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': now_utc
        }).fetchall()

        # Format the results
        formatted_result = []
        for row in result:
            agent_name = row[0]  # Agent's name

            # Skip if agent_name is None
            if agent_name is None:
                continue

            total_acw_duration = row[1] or 0  # Total ACW duration in seconds
            total_contacts = row[2] or 0  # Total contacts handled

            # Calculate average after contact work time
            if total_contacts > 0:
                avg_after_contact_work_time = total_acw_duration / total_contacts
            else:
                avg_after_contact_work_time = 0

            # Append result with formatted time
            formatted_result.append({
                "name": agent_name,
                "average_after_contact_work_time_seconds": seconds_to_hms(int(avg_after_contact_work_time)) if avg_after_contact_work_time > 0 else "00:00:00"
            })

        return formatted_result

    except Exception as e:
        print(f"Error in fetch_average_after_contact_work_time_last_15_minutes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Working with the cdr table.
def fetch_average_agent_interaction_time_last_15_minutes(db: Session, user_time_zone: str) -> List[schemas.AverageAgentInteractionTimeResponse]:
    # Get the user's timezone
    user_tz = pytz.timezone(user_time_zone)
    now_user = datetime.now(user_tz)
    start_time_user = now_user - timedelta(minutes=15)

    # Convert user's time to UTC for querying
    start_time_utc = start_time_user.astimezone(pytz.utc)
    now_utc = now_user.astimezone(pytz.utc)

    print("Start Time (UTC):", start_time_utc)
    print("Now Time (UTC):", now_utc)

    # SQL query to calculate total interaction time and count for each agent, only where required fields are not null
    query = text("""
        SELECT
            cc_agent AS name,
            SUM(EXTRACT(EPOCH FROM (end_stamp - answer_stamp))) AS total_interaction_time,
            COUNT(uuid) AS call_count
        FROM
            cdr
        WHERE
            timestamp >= :start_time
            AND answer_stamp IS NOT NULL
            AND end_stamp IS NOT NULL
            AND cc_agent IS NOT NULL
        GROUP BY
            cc_agent;
    """)

    try:
        # Execute the query
        result = db.execute(query, {'start_time': start_time_utc}).fetchall()
        print("Query Result:", result)  # Log the raw query results

        processed_result = []
        for row in result:
            agent_name = row[0]  # Accessing the agent name
            total_interaction_time = row[1]  # Total interaction time in seconds
            call_count = row[2]  # Count of calls answered

            # Calculate the average interaction time in seconds
            average_interaction_time = total_interaction_time / call_count if call_count > 0 else 0

            # Create response object, converting seconds to HH:MM:SS format
            if agent_name:  # Ensure agent_name is a valid string before appending
                processed_result.append(
                    schemas.AverageAgentInteractionTimeResponse(
                        name=str(agent_name),
                        average_agent_interaction_time_seconds=seconds_to_hms(int(average_interaction_time))
                    )
                )

        return processed_result

    except Exception as e:
        print(f"Error fetching average agent interaction time: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


#-------------------------------- metrics for 30 minutes time interval ---------------------->

# Working with the cdr table.
def get_recent_agent_names_last_30_minutes(db: Session, user_time_zone: str) -> list[str]:
    user_tz = pytz.timezone(user_time_zone)
    default_tz = pytz.utc
    now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
    start_time_utc = now_utc - timedelta(minutes=30)

    print(f"Start Time (UTC): {start_time_utc}")
    print(f"End Time (UTC): {now_utc}")

    query = text("""
        SELECT DISTINCT cc_agent
        FROM cdr
        WHERE timestamp >= :start_time AND timestamp <= :end_time
          AND cc_agent IS NOT NULL
    """)
    
    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': now_utc
        })
        data = result.fetchall()
        print(f"Fetched {len(data)} records from the database.")
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    if not data:
        print("No data found for the specified time range.")

    agent_names = [row[0] for row in data]  # Get the agent names from the fetched data

    print("Agent names:", agent_names)  # Check what names were added
    return agent_names

# Working with the cdr table.
def fetch_agent_answer_rate_last_30_minutes(db: Session, user_time_zone: str) -> list:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    start_time_user_time = now_user_time - timedelta(minutes=30)

    # Convert the user's local times to UTC for querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    # SQL query to calculate the answer rate based on the `timestamp` column
    query = text("""  
        WITH agent_call_data AS (
            SELECT
                cc_agent AS agent_name,
                COUNT(CASE WHEN answer_stamp IS NOT NULL AND billsec > 0 THEN 1 END) AS calls_answered,
                COUNT(CASE WHEN answer_stamp IS NULL OR billsec = 0 THEN 1 END) AS no_answer_count
            FROM cdr
            WHERE timestamp >= :start_time
            AND timestamp <= :end_time
            AND cc_agent IS NOT NULL  -- Filter out records without an agent
            GROUP BY cc_agent
        )
        SELECT
            agent_name,
            ROUND(
                (SUM(calls_answered) * 100.0 / 
                 CASE
                    WHEN (SUM(no_answer_count) + SUM(calls_answered)) = 0 THEN 1
                    ELSE (SUM(no_answer_count) + SUM(calls_answered))
                 END
                )
            ) AS agent_answer_rate
        FROM agent_call_data
        GROUP BY agent_name;
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

    return results

# Working with the cdr table.
def fetch_agent_non_response_last_30_minutes(
        db: Session, user_time_zone: str) -> List[schemas.AgentNonResponse]:
    # Convert the user's timezone to UTC for querying
    user_tz = pytz.timezone(user_time_zone)
    now_user = datetime.now(user_tz)

    # Calculate the start time as 30 minutes before the current time in the user's time zone
    start_time_user = now_user - timedelta(minutes=30)

    # Convert to UTC for the query
    start_time_utc = start_time_user.astimezone(pytz.utc)
    now_utc = now_user.astimezone(pytz.utc)

    # SQL query to sum non-answered calls for each agent in the last 15 minutes
    query = text("""  
        SELECT
            cc_agent AS name,
            COUNT(*) AS no_answer_count
        FROM
            cdr
        WHERE
            timestamp >= :start_time AND
            timestamp <= :end_time AND
            answer_stamp IS NULL
        GROUP BY
            cc_agent;
    """)

    # Execute the query
    result = db.execute(query, {'start_time': start_time_utc, 'end_time': now_utc}).fetchall()

    # Process the data, ensuring no None values for name, and divide the count by 3
    processed_result = [
        schemas.AgentNonResponse(
            name=row[0],  # Agent name
            no_answer_count=(row[1] // 3) if row[1] is not None else 0  # Count of non-responses divided by 3
        ) for row in result if row[0] is not None  # Filter out None names
    ]

    # Ensure all agents are represented, even if they have 0 non-responses
    if not processed_result:
        return [schemas.AgentNonResponse(name="No Agents", no_answer_count=0)]

    return processed_result

# working from the historical agent's table
def fetch_agent_on_contact_time_last_30_minutes(db: Session, user_time_zone: str) -> list:
    # Convert the user's timezone to UTC for querying
    user_tz = pytz.timezone(user_time_zone)
    now_user = datetime.now(user_tz)
    start_time_user = now_user - timedelta(minutes=30)

    # Convert user's time to UTC for querying
    start_time_utc = start_time_user.astimezone(pytz.utc)
    now_utc = now_user.astimezone(pytz.utc)

    # Query to fetch all relevant data within the time frame from the CDR table
    query = text("""
        SELECT 
            cc_agent, 
            end_stamp, 
            answer_stamp,
            timestamp
        FROM 
            cdr
        WHERE 
            timestamp >= :start_time 
            AND timestamp <= :end_time
        ORDER BY timestamp
    """)

    # Execute the query
    result = db.execute(query, {
        'start_time': start_time_utc,
        'end_time': now_utc
    }).fetchall()

    formatted_result = []
    total_contact_time = {}  # Dictionary to store total contact time per agent

    for row in result:
        agent_name = row[0]  # cc_agent
        end_stamp = row[1]   # end_stamp
        answer_stamp = row[2] # answer_stamp
        call_timestamp = row[3]  # timestamp

        # Ensure that we only process records with a valid agent name and non-null stamps
        if agent_name and end_stamp and answer_stamp:
            # Calculate the contact duration as the difference between end_stamp and answer_stamp
            contact_duration = (end_stamp - answer_stamp).total_seconds()

            # Convert call's timestamp to the user's local time for comparison
            call_timestamp_local = call_timestamp.astimezone(user_tz)

            # Check if the call falls within the last 15 minutes in the user's local time
            if start_time_user <= call_timestamp_local <= now_user:
                # Accumulate contact time for each agent
                if agent_name not in total_contact_time:
                    total_contact_time[agent_name] = 0  # Initialize if not already in dict
                total_contact_time[agent_name] += contact_duration  # Sum up the durations

    # Format the results for output
    for agent_name, total_seconds in total_contact_time.items():
        # Convert total seconds to timedelta for formatting
        delta = timedelta(seconds=total_seconds)
        formatted_time = str(delta).split()[-1]  # Get the time part

        formatted_result.append({
            "name": agent_name,
            "total_on_contact_time_seconds": formatted_time  # Format total time as a string
        })

    return formatted_result

# Working with the cdr table.
def fetch_agent_online_time_last_30_minutes(db: Session, user_time_zone: str) -> List[schemas.AgentOnlineTime]:
    try:
        # Convert the user's timezone to UTC for querying
        user_tz = pytz.timezone(user_time_zone)
        now_user = datetime.now(user_tz)
        start_time_user = now_user - timedelta(minutes=30)

        # Convert user's local times to UTC for querying
        start_time_utc = start_time_user.astimezone(pytz.utc)
        now_utc = now_user.astimezone(pytz.utc)  # Current UTC time

        # SQL query to calculate online time for each "Available" period
        query = text("""
            WITH available_periods AS (
                SELECT 
                    name,
                    timestamp AS available_timestamp,
                    LEAD(timestamp) OVER (PARTITION BY name ORDER BY timestamp) AS next_timestamp,
                    status
                FROM historical_agents_metrics
                WHERE timestamp >= :start_time AND timestamp <= :end_time
                ORDER BY name, timestamp
            )
            SELECT 
                name,
                SUM(EXTRACT(EPOCH FROM (COALESCE(next_timestamp, now()) - available_timestamp))) AS online_time
            FROM available_periods
            WHERE status = 'Available'
            GROUP BY name;
        """)

        # Fetch the results from the database
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': now_utc
        }).fetchall()

        # Format results
        formatted_result = []
        for row in result:
            name, total_online_time = row
            # Convert total_online_time to HH:MM:SS without microseconds
            formatted_result.append({
                "name": name,
                "online_time": seconds_to_hms(int(total_online_time))  # Ensure only seconds are used
            })

        return formatted_result
    except Exception as e:
        print(f"Error in fetch_agent_online_time_last_15_minutes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# working from the historical agent's table.
def fetch_non_productive_time_last_30_minutes(db: Session, user_time_zone: str) -> list:
    try:
        # Convert the user's timezone to UTC
        user_tz = pytz.timezone(user_time_zone)
        now_user = datetime.now(user_tz)
        start_time_user = now_user - timedelta(minutes=30)

        # Convert to UTC
        start_time_utc = start_time_user.astimezone(pytz.utc)
        now_utc = now_user.astimezone(pytz.utc)

        # SQL query to fetch all status records (including "On break" statuses)
        query = text("""
            WITH status_changes AS (
                SELECT 
                    ham.name,
                    ham.status,
                    ham.timestamp,
                    LEAD(ham.status) OVER (PARTITION BY ham.name ORDER BY ham.timestamp) AS next_status,
                    LEAD(ham.timestamp) OVER (PARTITION BY ham.name ORDER BY ham.timestamp) AS next_timestamp
                FROM historical_agents_metrics ham
                WHERE ham.timestamp >= :start_time 
                  AND ham.timestamp <= :end_time
            )
            SELECT 
                csp.name,
                csp.status,
                csp.timestamp,
                csp.next_status,
                csp.next_timestamp
            FROM status_changes csp
            WHERE csp.status = 'On Break'
              AND csp.next_status != 'On Break';
        """)

        # Fetch results from the database
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': now_utc
        }).fetchall()

        # Calculate the non-productive time for each agent
        formatted_result = []
        for row in result:
            name, status, on_break_timestamp, next_status, next_timestamp = row

            # Calculate non-productive time in seconds
            non_productive_time_seconds = (next_timestamp - on_break_timestamp).total_seconds()

            # Convert seconds to HH:MM:SS format
            formatted_result.append({
                "name": name,
                "non_productive_time_seconds": seconds_to_hms(int(non_productive_time_seconds)) if non_productive_time_seconds else "00:00:00"
            })

        # Group results by agent and sum non-productive times
        agent_times = {}
        for entry in formatted_result:
            name = entry["name"]
            if name in agent_times:
                # Sum non-productive times for the same agent
                current_time = agent_times[name]
                agent_times[name] = seconds_to_hms(int(current_time.split(":")[0]) * 3600 + int(current_time.split(":")[1]) * 60 + int(current_time.split(":")[2]) + int(entry["non_productive_time_seconds"].split(":")[2]))
            else:
                agent_times[name] = entry["non_productive_time_seconds"]

        # Return the result in the desired format
        return [{"name": name, "non_productive_time_seconds": time} for name, time in agent_times.items()]

    except Exception as e:
        print(f"Error in fetch_non_productive_time_last_15_minutes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Working with the cdr table.
def fetch_agent_contacts_handled_last_30_minutes(db: Session, user_time_zone: str) -> List[Dict[str, str]]:
    try:
        # Convert the user's timezone to UTC for querying
        user_tz = pytz.timezone(user_time_zone)

        # Get current time in user's time zone and convert it to UTC
        now_user = datetime.now(user_tz)
        start_time_user = now_user - timedelta(minutes=30)
        start_time_utc = start_time_user.astimezone(pytz.utc)

        # SQL query to track and sum the count of answered calls for each agent in the last 15 minutes from the cdr table
        query = text("""
            SELECT 
                cc_agent AS name, 
                COUNT(answer_stamp) AS total_calls_answered
            FROM 
                cdr
            WHERE 
                timestamp >= :start_time
                AND answer_stamp IS NOT NULL
                AND cc_agent IS NOT NULL
            GROUP BY 
                cc_agent
        """)

        # Execute the SQL query using UTC for querying
        result = db.execute(query, {
            'start_time': start_time_utc
        }).fetchall()

        # Format the results, ensuring "0" is returned when the count is zero
        formatted_result = [
            {
                "name": row[0],  # Access tuple elements by index
                "contacts_handled": row[1]  # Directly use the integer result
            } for row in result
        ]

        # Handle case where no agents are returned
        if not formatted_result:
            return [{"name": "No Agents", "contacts_handled": 0}]  # Return a default entry

        return formatted_result

    except Exception as e:
        print(f"Error executing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Working with the cdr table.
def fetch_average_after_contact_work_time_last_30_minutes(
        db: Session, user_time_zone: str) -> List[Dict[str, any]]:
    try:
        # Convert the user's timezone to UTC for querying
        user_tz = pytz.timezone(user_time_zone)
        now_user = datetime.now(user_tz)
        start_time_user = now_user - timedelta(minutes=30)

        # Convert user's time to UTC for querying
        start_time_utc = start_time_user.astimezone(pytz.utc)
        now_utc = now_user.astimezone(pytz.utc)

        # SQL query to fetch answer_stamp and end_stamp from cdr table
        query = text("""
            SELECT 
                cc_agent,
                SUM(EXTRACT(EPOCH FROM (end_stamp - answer_stamp))) AS total_acw_duration,
                COUNT(*) AS total_contacts
            FROM 
                cdr
            WHERE 
                timestamp >= :start_time 
                AND timestamp <= :end_time 
                AND end_stamp IS NOT NULL
                AND answer_stamp IS NOT NULL
            GROUP BY 
                cc_agent
        """)

        # Execute the query
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': now_utc
        }).fetchall()

        # Format the results
        formatted_result = []
        for row in result:
            agent_name = row[0]  # Agent's name

            # Skip if agent_name is None
            if agent_name is None:
                continue

            total_acw_duration = row[1] or 0  # Total ACW duration in seconds
            total_contacts = row[2] or 0  # Total contacts handled

            # Calculate average after contact work time
            if total_contacts > 0:
                avg_after_contact_work_time = total_acw_duration / total_contacts
            else:
                avg_after_contact_work_time = 0

            # Append result with formatted time
            formatted_result.append({
                "name": agent_name,
                "average_after_contact_work_time_seconds": seconds_to_hms(int(avg_after_contact_work_time)) if avg_after_contact_work_time > 0 else "00:00:00"
            })

        return formatted_result

    except Exception as e:
        print(f"Error in fetch_average_after_contact_work_time_last_15_minutes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Working with the cdr table.
def fetch_average_agent_interaction_time_last_30_minutes(db: Session, user_time_zone: str) -> List[schemas.AverageAgentInteractionTimeResponse]:
    # Get the user's timezone
    user_tz = pytz.timezone(user_time_zone)
    now_user = datetime.now(user_tz)
    start_time_user = now_user - timedelta(minutes=30)

    # Convert user's time to UTC for querying
    start_time_utc = start_time_user.astimezone(pytz.utc)
    now_utc = now_user.astimezone(pytz.utc)

    print("Start Time (UTC):", start_time_utc)
    print("Now Time (UTC):", now_utc)

    # SQL query to calculate total interaction time and count for each agent, only where required fields are not null
    query = text("""
        SELECT
            cc_agent AS name,
            SUM(EXTRACT(EPOCH FROM (end_stamp - answer_stamp))) AS total_interaction_time,
            COUNT(uuid) AS call_count
        FROM
            cdr
        WHERE
            timestamp >= :start_time
            AND answer_stamp IS NOT NULL
            AND end_stamp IS NOT NULL
            AND cc_agent IS NOT NULL
        GROUP BY
            cc_agent;
    """)

    try:
        # Execute the query
        result = db.execute(query, {'start_time': start_time_utc}).fetchall()
        print("Query Result:", result)  # Log the raw query results

        processed_result = []
        for row in result:
            agent_name = row[0]  # Accessing the agent name
            total_interaction_time = row[1]  # Total interaction time in seconds
            call_count = row[2]  # Count of calls answered

            # Calculate the average interaction time in seconds
            average_interaction_time = total_interaction_time / call_count if call_count > 0 else 0

            # Create response object, converting seconds to HH:MM:SS format
            if agent_name:  # Ensure agent_name is a valid string before appending
                processed_result.append(
                    schemas.AverageAgentInteractionTimeResponse(
                        name=str(agent_name),
                        average_agent_interaction_time_seconds=seconds_to_hms(int(average_interaction_time))
                    )
                )

        return processed_result

    except Exception as e:
        print(f"Error fetching average agent interaction time: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


#-------------------------------- metrics for Today(Since 12 am) minutes time interval ---------------------->

# Working with the cdr table.
def get_recent_agent_names_today(db: Session, user_time_zone: str) -> list[str]:
    user_tz = pytz.timezone(user_time_zone)
    default_tz = pytz.utc
    now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)

    # Get the start of today in UTC
    start_time_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    print(f"Start Time (UTC): {start_time_utc}")
    print(f"End Time (UTC): {now_utc}")

    query = text("""  
        SELECT DISTINCT cc_agent 
        FROM cdr 
        WHERE timestamp >= :start_time AND timestamp <= :end_time 
          AND cc_agent IS NOT NULL
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': now_utc
        })
        data = result.fetchall()
        print(f"Fetched {len(data)} records from the database.")
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    if not data:
        print("No data found for the specified time range.")

    agent_names = [row[0] for row in data]  # Get the agent names from the fetched data

    print("Agent names:", agent_names)  # Check what names were added
    return agent_names

# Working with the cdr table.
def fetch_agent_answer_rate_today(db: Session, user_time_zone: str) -> list:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Calculate the current time and start time in the user's time zone
    now_user_time = datetime.now(user_tz)
    
    # Get the start of today in the user's time zone
    start_time_user_time = now_user_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert the user's local times to UTC for querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = now_user_time.astimezone(pytz.utc)

    # SQL query to calculate the answer rate based on the `timestamp` column
    query = text("""
        WITH agent_call_data AS (
            SELECT
                cc_agent AS agent_name,
                COUNT(CASE WHEN answer_stamp IS NOT NULL AND billsec > 0 THEN 1 END) AS calls_answered,
                COUNT(CASE WHEN answer_stamp IS NULL OR billsec = 0 THEN 1 END) AS no_answer_count
            FROM cdr
            WHERE timestamp >= :start_time
            AND timestamp <= :end_time
            AND cc_agent IS NOT NULL  -- Filter out records without an agent
            GROUP BY cc_agent
        )
        SELECT
            agent_name,
            ROUND(  -- Round to get whole percentage
                (SUM(calls_answered) * 100.0 / 
                 CASE
                    WHEN (SUM(no_answer_count) + SUM(calls_answered)) = 0 THEN 1
                    ELSE (SUM(no_answer_count) + SUM(calls_answered))
                 END
                )
            ) AS agent_answer_rate
        FROM agent_call_data
        GROUP BY agent_name;
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

    return results

# Working with the cdr table.
def fetch_agent_non_response_today(
        db: Session, user_time_zone: str) -> List[schemas.AgentNonResponse]:
    # Convert the user's timezone to UTC for querying
    user_tz = pytz.timezone(user_time_zone)
    now_user = datetime.now(user_tz)

    # Get the start of today in the user's time zone
    start_time_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert to UTC for the query
    start_time_utc = start_time_user.astimezone(pytz.utc)
    now_utc = now_user.astimezone(pytz.utc)

    # SQL query to sum non-answered calls for each agent
    query = text("""  
        SELECT
            cc_agent AS name,
            COUNT(*) AS no_answer_count
        FROM
            cdr
        WHERE
            timestamp >= :start_time AND
            timestamp <= :end_time AND
            answer_stamp IS NULL
        GROUP BY
            cc_agent;
    """)

    # Execute the query
    result = db.execute(query, {'start_time': start_time_utc, 'end_time': now_utc}).fetchall()

    # Process the data, ensuring no None values for name, and divide the count by 3
    processed_result = [
        schemas.AgentNonResponse(
            name=row[0],  # Agent name
            no_answer_count=(row[1] // 3) if row[1] is not None else 0  # Count of non-responses divided by 3
        ) for row in result if row[0] is not None  # Filter out None names
    ]

    # Ensure all agents are represented, even if they have 0 non-responses
    if not processed_result:
        return [schemas.AgentNonResponse(name="No Agents", no_answer_count=0)]

    return processed_result

# Working with the cdr table.
def fetch_agent_contacts_handled_today(db: Session, user_time_zone: str) -> List[Dict[str, str]]:
    try:
        # Convert the user's timezone to UTC for querying
        user_tz = pytz.timezone(user_time_zone)

        # Get current time in user's time zone and set the start time to today's midnight
        now_user = datetime.now(user_tz)
        start_time_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)
        start_time_utc = start_time_user.astimezone(pytz.utc)

        # SQL query to track and sum the count of answered calls for each agent since 12 AM
        query = text("""
            SELECT 
                cc_agent AS name, 
                COUNT(answer_stamp) AS total_calls_answered
            FROM 
                cdr
            WHERE 
                timestamp >= :start_time
                AND answer_stamp IS NOT NULL
                AND cc_agent IS NOT NULL
            GROUP BY 
                cc_agent
        """)

        # Execute the SQL query using UTC for querying
        result = db.execute(query, {
            'start_time': start_time_utc
        }).fetchall()

        # Format the results, ensuring "0" is returned when the count is zero
        formatted_result = [
            {
                "name": row[0],  # Access tuple elements by index
                "contacts_handled": row[1]  # Directly use the integer result
            } for row in result
        ]

        # Handle case where no agents are returned
        if not formatted_result:
            return [{"name": "No Agents", "contacts_handled": 0}]  # Return a default entry

        return formatted_result

    except Exception as e:
        print(f"Error executing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Working with the cdr table.
def fetch_agent_on_contact_time_today(db: Session, user_time_zone: str) -> list:
    # Convert the user's timezone to UTC for querying
    user_tz = pytz.timezone(user_time_zone)
    now_user = datetime.now(user_tz)

    # Get the start of today in the user's local time
    start_time_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert user's time to UTC for querying
    start_time_utc = start_time_user.astimezone(pytz.utc)
    now_utc = now_user.astimezone(pytz.utc)

    # Query to fetch relevant data from the CDR table since 12 AM
    query = text("""
        SELECT 
            cc_agent, 
            answer_stamp, 
            end_stamp, 
            timestamp
        FROM 
            cdr
        WHERE 
            timestamp >= :start_time 
            AND timestamp <= :end_time
            AND answer_stamp IS NOT NULL
            AND end_stamp IS NOT NULL
        ORDER BY timestamp
    """)

    # Execute the query
    result = db.execute(query, {
        'start_time': start_time_utc,
        'end_time': now_utc
    }).fetchall()

    formatted_result = []
    total_contact_time = {}  # Dictionary to store total contact time per agent

    for row in result:
        agent_name = row[0]  # cc_agent
        answer_stamp = row[1]  # Start of contact
        end_stamp = row[2]  # End of contact
        call_timestamp = row[3]  # timestamp

        # Ensure that we only process records with a valid agent name
        if agent_name:
            # Convert call's timestamp to the user's local time for comparison
            call_timestamp_local = call_timestamp.astimezone(user_tz)

            # Check if the call falls within today in the user's local time
            if start_time_user <= call_timestamp_local <= now_user:
                # Calculate the contact time as the difference between end_stamp and answer_stamp
                contact_duration = (end_stamp - answer_stamp).total_seconds()

                # Accumulate contact time for each agent
                if agent_name not in total_contact_time:
                    total_contact_time[agent_name] = 0  # Initialize if not already in dict
                total_contact_time[agent_name] += contact_duration  # Sum up the durations

    # Format the results for output
    for agent_name, total_seconds in total_contact_time.items():
        # Convert total seconds to timedelta for formatting
        delta = timedelta(seconds=total_seconds)
        formatted_time = str(delta).split()[-1]  # Get the time part

        formatted_result.append({
            "name": agent_name,
            "total_on_contact_time_seconds": formatted_time  # Format total time as a string
        })

    return formatted_result

# working from the historical agent's table
def fetch_agent_online_time_today(db: Session, user_time_zone: str) -> List[schemas.AgentOnlineTime]:
    try:
        # Convert the user's timezone to UTC for querying
        user_tz = pytz.timezone(user_time_zone)
        
        # Get the current time in the user's timezone
        now_user = datetime.now(user_tz)
        
        # Set start_time_user to 12 AM of the current day in the user's timezone
        start_time_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)

        # Convert user's local times to UTC for querying
        start_time_utc = start_time_user.astimezone(pytz.utc)
        now_utc = now_user.astimezone(pytz.utc)  # Current UTC time

        # SQL query to calculate online time for each "Available" period
        query = text("""
            WITH available_periods AS (
                SELECT 
                    name,
                    timestamp AS available_timestamp,
                    LEAD(timestamp) OVER (PARTITION BY name ORDER BY timestamp) AS next_timestamp,
                    status
                FROM historical_agents_metrics
                WHERE timestamp >= :start_time AND timestamp <= :end_time
                ORDER BY name, timestamp
            )
            SELECT 
                name,
                SUM(EXTRACT(EPOCH FROM (COALESCE(next_timestamp, now()) - available_timestamp))) AS online_time
            FROM available_periods
            WHERE status = 'Available'
            GROUP BY name;
        """)

        # Fetch the results from the database
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': now_utc
        }).fetchall()

        # Format results
        formatted_result = []
        for row in result:
            name, total_online_time = row
            # Convert total_online_time to HH:MM:SS without microseconds
            formatted_result.append({
                "name": name,
                "online_time": seconds_to_hms(int(total_online_time))  # Ensure only seconds are used
            })

        return formatted_result
    except Exception as e:
        print(f"Error in fetch_agent_online_time_today_since_12_am: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# working from the historical agent's table
def fetch_non_productive_time_today(db: Session, user_time_zone: str) -> list:
    try:
        # Convert the user's timezone to UTC
        user_tz = pytz.timezone(user_time_zone)
        now_user = datetime.now(user_tz)
        
        # Set the start time to today's midnight (00:00:00) in the user's timezone
        start_time_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)

        # Convert both start and end times to UTC
        start_time_utc = start_time_user.astimezone(pytz.utc)
        now_utc = now_user.astimezone(pytz.utc)

        # SQL query to fetch all status records (including "On break" statuses) for today since 12 AM
        query = text("""
            WITH status_changes AS (
                SELECT 
                    ham.name,
                    ham.status,
                    ham.timestamp,
                    LEAD(ham.status) OVER (PARTITION BY ham.name ORDER BY ham.timestamp) AS next_status,
                    LEAD(ham.timestamp) OVER (PARTITION BY ham.name ORDER BY ham.timestamp) AS next_timestamp
                FROM historical_agents_metrics ham
                WHERE ham.timestamp >= :start_time 
                  AND ham.timestamp <= :end_time
            )
            SELECT 
                csp.name,
                csp.status,
                csp.timestamp,
                csp.next_status,
                csp.next_timestamp
            FROM status_changes csp
            WHERE csp.status = 'On Break'
              AND csp.next_status != 'On Break';
        """)

        # Fetch results from the database
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': now_utc
        }).fetchall()

        # Calculate the non-productive time for each agent
        formatted_result = []
        for row in result:
            name, status, on_break_timestamp, next_status, next_timestamp = row

            # Calculate non-productive time in seconds
            non_productive_time_seconds = (next_timestamp - on_break_timestamp).total_seconds()

            # Convert seconds to HH:MM:SS format
            formatted_result.append({
                "name": name,
                "non_productive_time_seconds": seconds_to_hms(int(non_productive_time_seconds)) if non_productive_time_seconds else "00:00:00"
            })

        # Group results by agent and sum non-productive times
        agent_times = {}
        for entry in formatted_result:
            name = entry["name"]
            if name in agent_times:
                # Sum non-productive times for the same agent
                current_time = agent_times[name]
                agent_times[name] = seconds_to_hms(int(current_time.split(":")[0]) * 3600 + int(current_time.split(":")[1]) * 60 + int(current_time.split(":")[2]) + int(entry["non_productive_time_seconds"].split(":")[2]))
            else:
                agent_times[name] = entry["non_productive_time_seconds"]

        # Return the result in the desired format
        return [{"name": name, "non_productive_time_seconds": time} for name, time in agent_times.items()]

    except Exception as e:
        print(f"Error in fetch_non_productive_time_today: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Working with the cdr table.
def fetch_average_after_contact_work_time_today(
        db: Session, user_time_zone: str) -> List[Dict[str, any]]:
    try:
        # Convert the user's timezone to UTC for querying
        user_tz = pytz.timezone(user_time_zone)
        now_user = datetime.now(user_tz)

        # Get the start of today in the user's local time
        start_time_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)

        # Convert user's time to UTC for querying
        start_time_utc = start_time_user.astimezone(pytz.utc)
        now_utc = now_user.astimezone(pytz.utc)

        # SQL query to fetch after contact work duration from cdr table using the timestamp column
        query = text("""
            SELECT 
                cc_agent,
                SUM(EXTRACT(EPOCH FROM (end_stamp - answer_stamp))) AS total_acw_duration,
                COUNT(*) AS total_contacts
            FROM 
                cdr
            WHERE 
                timestamp >= :start_time 
                AND timestamp <= :end_time 
                AND end_stamp IS NOT NULL
                AND answer_stamp IS NOT NULL
            GROUP BY 
                cc_agent
        """)

        # Execute the query
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': now_utc
        }).fetchall()

        # Format the results
        formatted_result = []
        for row in result:
            agent_name = row[0] if row[0] is not None else "Unknown Agent"  # Handle None names
            total_acw_duration = row[1] or 0  # Total ACW duration in seconds
            total_contacts = row[2] or 0  # Total contacts handled

            # Calculate average after contact work time
            if total_contacts > 0:
                avg_after_contact_work_time = total_acw_duration / total_contacts
            else:
                avg_after_contact_work_time = 0

            # Append result with formatted time
            formatted_result.append({
                "name": agent_name,
                "average_after_contact_work_time_seconds": seconds_to_hms(int(avg_after_contact_work_time)) if avg_after_contact_work_time > 0 else "00:00:00"
            })

        return formatted_result

    except Exception as e:
        print(f"Error in fetch_average_after_contact_work_time_today: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Working with the cdr table.
def fetch_average_agent_interaction_time_today(db: Session, user_time_zone: str) -> List[schemas.AverageAgentInteractionTimeResponse]:
    # Get the user's timezone and set the start of the day (12 AM)
    user_tz = pytz.timezone(user_time_zone)
    now_user = datetime.now(user_tz)
    start_time_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)  # Set to today at 12 AM in user's timezone

    # Convert user's start and end times to UTC for querying
    start_time_utc = start_time_user.astimezone(pytz.utc)
    now_utc = now_user.astimezone(pytz.utc)

    print("Start Time (UTC):", start_time_utc)
    print("Now Time (UTC):", now_utc)

    # SQL query to calculate total interaction time and count for each agent
    query = text("""
        SELECT
            cc_agent AS name,
            SUM(EXTRACT(EPOCH FROM (end_stamp - answer_stamp))) AS total_interaction_time,
            COUNT(uuid) AS call_count
        FROM
            cdr
        WHERE
            timestamp >= :start_time
            AND answer_stamp IS NOT NULL
            AND end_stamp IS NOT NULL
            AND cc_agent IS NOT NULL
        GROUP BY
            cc_agent;
    """)

    try:
        # Execute the query
        result = db.execute(query, {'start_time': start_time_utc}).fetchall()
        print("Query Result:", result)  # Log the raw query results

        processed_result = []
        for row in result:
            agent_name = row[0]  # Accessing the agent name
            total_interaction_time = row[1]  # Total interaction time in seconds
            call_count = row[2]  # Count of calls answered

            # Calculate the average interaction time in seconds
            average_interaction_time = total_interaction_time / call_count if call_count > 0 else 0

            # Create response object, converting seconds to HH:MM:SS format
            if agent_name:  # Ensure agent_name is a valid string before appending
                processed_result.append(
                    schemas.AverageAgentInteractionTimeResponse(
                        name=str(agent_name),
                        average_agent_interaction_time_seconds=seconds_to_hms(int(average_interaction_time))
                    )
                )

        return processed_result

    except Exception as e:
        print(f"Error fetching average agent interaction time: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ------------------------ to get the metrics for custom date range ------------------->

# Working with the cdr table.
def get_recent_agent_names_for_date_range(db: Session, user_time_zone: str,
                                          start_date: str,
                                          end_date: str) -> list[str]:
    user_tz = pytz.timezone(user_time_zone)

    # Convert start and end date strings to datetime objects
    start_time_user_tz = datetime.fromisoformat(start_date).astimezone(user_tz)
    end_time_user_tz = datetime.fromisoformat(end_date).astimezone(user_tz)

    # Convert both to UTC to match the database timestamps
    start_time_utc = start_time_user_tz.astimezone(pytz.utc)
    end_time_utc = end_time_user_tz.astimezone(pytz.utc)

    print(f"Start Time (UTC): {start_time_utc}")
    print(f"End Time (UTC): {end_time_utc}")

    query = text("""  
        SELECT DISTINCT cc_agent 
        FROM cdr 
        WHERE timestamp >= :start_time AND timestamp <= :end_time 
          AND cc_agent IS NOT NULL
    """)

    try:
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        })
        data = result.fetchall()
        print(f"Fetched {len(data)} records from the database.")
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    if not data:
        print("No data found for the specified time range.")

    agent_names = [row[0] for row in data]  # Get the agent names from the fetched data

    print("Agent names:", agent_names)  # Check what names were added
    return agent_names

# Working with the cdr table.
def fetch_agent_answer_rate_for_date_range(db: Session, user_time_zone: str,
                                           start_date: str,
                                           end_date: str) -> list:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz)

    # Convert the user's local times to UTC for querying the database
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    # SQL query to calculate the answer rate based on the `timestamp` column
    query = text("""  
        WITH agent_call_data AS (
            SELECT
                cc_agent AS agent_name,
                COUNT(CASE WHEN answer_stamp IS NOT NULL AND billsec > 0 THEN 1 END) AS calls_answered,
                COUNT(CASE WHEN answer_stamp IS NULL OR billsec = 0 THEN 1 END) AS no_answer_count
            FROM cdr
            WHERE timestamp >= :start_time
            AND timestamp <= :end_time
            AND cc_agent IS NOT NULL  -- Filter out records without an agent
            GROUP BY cc_agent
        )
        SELECT
            agent_name,
            ROUND(  -- Round to get whole percentage
                (SUM(calls_answered) * 100.0 / 
                 CASE
                    WHEN (SUM(no_answer_count) + SUM(calls_answered)) = 0 THEN 1
                    ELSE (SUM(no_answer_count) + SUM(calls_answered))
                 END
                )
            ) AS agent_answer_rate
        FROM agent_call_data
        GROUP BY agent_name;
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

    return results

# Working with the cdr table.
def fetch_agent_non_response_for_date_range(
        db: Session, user_time_zone: str, start_date: str,
        end_date: str) -> list[schemas.AgentNonResponse]:

    # Convert the user's timezone based on input
    user_tz = pytz.timezone(user_time_zone)

    # Convert the start and end dates from the UI (ISO format) to the user's timezone
    start_time_user = datetime.fromisoformat(start_date).astimezone(user_tz)
    end_time_user = datetime.fromisoformat(end_date).astimezone(user_tz)

    # Convert the times to UTC for querying the database
    start_time_utc = start_time_user.astimezone(pytz.utc)
    end_time_utc = end_time_user.astimezone(pytz.utc)

    # SQL query to sum non-answered calls for each agent within the specified date range
    query = text("""
        SELECT
            cc_agent AS name,
            COUNT(*) AS no_answer_count
        FROM
            cdr
        WHERE
            timestamp >= :start_time AND
            timestamp <= :end_time AND
            answer_stamp IS NULL
        GROUP BY
            cc_agent;
    """)

    try:
        # Execute the query with the date range
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()
        print("Query result:", result)  # Debugging line to see the raw query results
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    # Process the data, filtering out None names and dividing the count by 3
    processed_result = [
        schemas.AgentNonResponse(
            name=row[0],  # Agent name
            no_answer_count=(row[1] // 3) if row[1] is not None else 0  # Count of non-responses divided by 3
        ) for row in result if row[0] is not None  # Filter out None names
    ]

    # Return a default response if no valid data was found
    if not processed_result:
        return [schemas.AgentNonResponse(name="No Agents", no_answer_count=0)]

    return processed_result

# Working with the cdr table.
def fetch_agent_on_contact_time_for_date_range(db: Session,
                                               user_time_zone: str,
                                               start_date: str,
                                               end_date: str) -> list:
    # Convert the user's timezone to UTC for querying
    user_tz = pytz.timezone(user_time_zone)

    # Parse the start and end dates from the string format
    start_time_user = datetime.fromisoformat(start_date).astimezone(user_tz)
    end_time_user = datetime.fromisoformat(end_date).astimezone(user_tz)

    # Convert user's time to UTC for querying
    start_time_utc = start_time_user.astimezone(pytz.utc)
    end_time_utc = end_time_user.astimezone(pytz.utc)

    # SQL query to fetch agent on-contact time within the date range
    query = text("""
        SELECT 
            cc_agent, 
            answer_stamp, 
            end_stamp, 
            timestamp
        FROM 
            cdr
        WHERE 
            timestamp >= :start_time 
            AND timestamp <= :end_time
            AND answer_stamp IS NOT NULL
            AND end_stamp IS NOT NULL
        ORDER BY timestamp
    """)

    result = db.execute(query, {
        'start_time': start_time_utc,
        'end_time': end_time_utc
    }).fetchall()

    formatted_result = []
    total_contact_time = {}  # Dictionary to store total contact time per agent

    # Process each row of the result
    for row in result:
        agent_name = row[0]  # cc_agent
        answer_stamp = row[1]  # Start of contact
        end_stamp = row[2]  # End of contact
        call_timestamp = row[3]  # timestamp

        # Ensure that we only process records with a valid agent name
        if agent_name:
            # Convert call's timestamp to the user's local time for comparison
            call_timestamp_local = call_timestamp.astimezone(user_tz)

            # Check if the call falls within the specified date range in the user's local time
            if start_time_user <= call_timestamp_local <= end_time_user:
                # Calculate the contact time as the difference between end_stamp and answer_stamp
                contact_duration = (end_stamp - answer_stamp).total_seconds()

                # Accumulate contact time for each agent
                if agent_name not in total_contact_time:
                    total_contact_time[agent_name] = 0  # Initialize if not already in dict
                total_contact_time[agent_name] += contact_duration  # Sum up the durations

    # Format the results for output
    for agent_name, total_seconds in total_contact_time.items():
        # Convert total seconds to timedelta for formatting
        delta = timedelta(seconds=total_seconds)
        formatted_time = str(delta).split()[-1]  # Get the time part

        formatted_result.append({
            "name": agent_name,
            "total_on_contact_time_seconds": formatted_time  # Format total time as a string
        })

    # Handle case where no agents are returned
    if not formatted_result:
        return [{"name": "No Agents", "total_on_contact_time_seconds": "00:00:00"}]

    return formatted_result

# Working with the cdr table.
def fetch_agent_online_time_for_date_range(db: Session, user_time_zone: str,
                                           start_date: str,
                                           end_date: str) -> List[schemas.AgentOnlineTime]:
    try:
        # Convert the user's timezone based on input
        user_tz = pytz.timezone(user_time_zone)

        # Convert the start and end dates from the UI (ISO format) to the user's timezone
        start_time_user = datetime.fromisoformat(start_date).astimezone(user_tz)
        end_time_user = datetime.fromisoformat(end_date).astimezone(user_tz)

        # Convert the times to UTC for querying the database
        start_time_utc = start_time_user.astimezone(pytz.utc)
        end_time_utc = end_time_user.astimezone(pytz.utc)

        # SQL query to calculate online time for "Available" status within the date range
        query = text("""
            WITH available_periods AS (
                SELECT 
                    name,
                    timestamp AS available_timestamp,
                    LEAD(timestamp) OVER (PARTITION BY name ORDER BY timestamp) AS next_timestamp,
                    status
                FROM historical_agents_metrics
                WHERE timestamp >= :start_time AND timestamp <= :end_time
                ORDER BY name, timestamp
            )
            SELECT 
                name,
                SUM(EXTRACT(EPOCH FROM (COALESCE(next_timestamp, :end_time) - available_timestamp))) AS online_time
            FROM available_periods
            WHERE status = 'Available'
            GROUP BY name;
        """)

        # Fetch the results from the database
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Process the results and format the online time
        formatted_result = []
        for row in result:
            name, total_online_time = row
            # Convert total_online_time to HH:MM:SS without microseconds
            formatted_result.append({
                "name": name,
                "online_time": seconds_to_hms(int(total_online_time))  # Ensure only seconds are used
            })

        return formatted_result

    except Exception as e:
        print(f"Error in fetch_agent_online_time_for_date_range: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Working with the cdr table.
def fetch_non_productive_time_for_date_range(db: Session, user_time_zone: str,
                                             start_date: str,
                                             end_date: str) -> list:
    try:
        # Convert the user's timezone based on input
        user_tz = pytz.timezone(user_time_zone)

        # Convert the start and end dates from the UI (ISO format) to the user's timezone
        start_time_user = datetime.fromisoformat(start_date).astimezone(user_tz)
        end_time_user = datetime.fromisoformat(end_date).astimezone(user_tz)

        # Convert the times to UTC for querying the database
        start_time_utc = start_time_user.astimezone(pytz.utc)
        end_time_utc = end_time_user.astimezone(pytz.utc)

        # SQL query to fetch all records for the interval
        query = text("""
            WITH status_periods AS (
                SELECT 
                    ham.name,
                    ham.timestamp,
                    ham.status,
                    LEAD(ham.timestamp) OVER (PARTITION BY ham.name ORDER BY ham.timestamp) AS next_timestamp
                FROM historical_agents_metrics ham
                WHERE ham.timestamp >= :start_time
                  AND ham.timestamp <= :end_time
            ),
            on_break_periods AS (
                SELECT
                    name,
                    timestamp AS on_break_timestamp,
                    next_timestamp
                FROM status_periods
                WHERE status = 'On Break'
            )
            SELECT
                obp.name,
                SUM(EXTRACT(EPOCH FROM (LEAST(obp.next_timestamp, :end_time) - obp.on_break_timestamp))) AS non_productive_time_seconds
            FROM on_break_periods obp
            GROUP BY obp.name;
        """)

        # Fetch results from the database
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Format the results to HH:MM:SS
        formatted_result = [
            {
                "name": name,
                "non_productive_time_seconds": seconds_to_hms(int(non_productive_time_seconds)) if non_productive_time_seconds else "00:00:00"
            }
            for name, non_productive_time_seconds in result
        ]

        return formatted_result

    except Exception as e:
        print(f"Error in fetch_non_productive_time_for_date_range: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Working with the cdr table.
def fetch_agent_contacts_handled_for_date_range(
        db: Session, user_time_zone: str, start_date: str,
        end_date: str) -> List[Dict[str, str]]:
    try:
        # Convert the user's timezone based on input
        user_tz = pytz.timezone(user_time_zone)

        # Convert the start and end dates from the UI (ISO format) to the user's timezone
        start_time_user = datetime.fromisoformat(start_date).astimezone(user_tz)
        end_time_user = datetime.fromisoformat(end_date).astimezone(user_tz)

        # Convert the times to UTC for querying the database
        start_time_utc = start_time_user.astimezone(pytz.utc)
        end_time_utc = end_time_user.astimezone(pytz.utc)

        # Log the UTC conversion for debugging
        print(f"Start Time UTC: {start_time_utc}, End Time UTC: {end_time_utc}")

        # SQL query to track and sum the count of answered calls for each agent within the date range
        query = text("""
            SELECT 
                cc_agent AS name, 
                COUNT(answer_stamp) AS total_calls_answered
            FROM 
                cdr
            WHERE 
                timestamp >= :start_time
                AND timestamp <= :end_time
                AND answer_stamp IS NOT NULL
                AND cc_agent IS NOT NULL
            GROUP BY 
                cc_agent
        """)

        # Execute the SQL query using UTC timestamps
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Check if the result is empty
        if not result:
            print("No records found for the given date range.")
            return [{"name": "No Agents", "contacts_handled": 0}]

        # Format the results, ensuring "0" is returned when the count is zero
        formatted_result = [
            {
                "name": row[0],  # Access tuple elements by index
                "contacts_handled": row[1] or 0  # Default to 0 if None
            } for row in result
        ]

        return formatted_result

    except Exception as e:
        # Log the error details
        print(f"Error in fetch_agent_contacts_handled_for_date_range: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Working with the cdr table.
def fetch_average_after_contact_work_time_for_date_range(
        db: Session, user_time_zone: str, start_date: str,
        end_date: str) -> List[Dict[str, any]]:
    try:
        # Convert the user's timezone based on input
        user_tz = pytz.timezone(user_time_zone)

        # Convert the start and end dates from the UI (ISO format) to the user's timezone
        start_time_user = datetime.fromisoformat(start_date).astimezone(user_tz)
        end_time_user = datetime.fromisoformat(end_date).astimezone(user_tz)

        # Convert the times to UTC for querying the database
        start_time_utc = start_time_user.astimezone(pytz.utc)
        end_time_utc = end_time_user.astimezone(pytz.utc)

        # SQL query to calculate average after contact work time
        query = text("""
            SELECT 
                cc_agent,
                SUM(EXTRACT(EPOCH FROM (end_stamp - answer_stamp))) AS total_acw_duration,
                COUNT(*) AS total_contacts
            FROM 
                cdr
            WHERE 
                timestamp >= :start_time 
                AND timestamp <= :end_time 
                AND end_stamp IS NOT NULL
                AND answer_stamp IS NOT NULL
            GROUP BY 
                cc_agent
        """)

        # Execute the query
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        # Format the results
        formatted_result = []
        for row in result:
            agent_name = row[0] if row[0] is not None else "Unknown Agent"  # Handle None names
            total_acw_duration = row[1] or 0  # Total ACW duration in seconds
            total_contacts = row[2] or 0  # Total contacts handled

            # Calculate average after contact work time
            if total_contacts > 0:
                avg_after_contact_work_time = total_acw_duration / total_contacts
            else:
                avg_after_contact_work_time = 0

            # Append result with formatted time
            formatted_result.append({
                "name": agent_name,
                "average_after_contact_work_time_seconds": seconds_to_hms(int(avg_after_contact_work_time)) if avg_after_contact_work_time > 0 else "00:00:00"
            })

        return formatted_result

    except Exception as e:
        print(f"Error in fetch_average_after_contact_work_time_for_date_range: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Working with the cdr table.
def fetch_average_agent_interaction_time_for_date_range(db: Session, user_time_zone: str, start_date: str, end_date: str) -> list[schemas.AverageAgentInteractionTimeResponse]:
    # Set the user's timezone based on the input parameter
    user_tz = pytz.timezone(user_time_zone)

    # Convert the user-provided start and end dates to datetime objects in the user's timezone
    start_time_user_time = datetime.fromisoformat(start_date).astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_time_user_time = datetime.fromisoformat(end_date).astimezone(user_tz).replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to UTC for database querying
    start_time_utc = start_time_user_time.astimezone(pytz.utc)
    end_time_utc = end_time_user_time.astimezone(pytz.utc)

    # Query to fetch the average agent interaction time and total calls per agent in the specified date range
    query = text("""
        SELECT
            cc_agent AS name,
            SUM(EXTRACT(EPOCH FROM (end_stamp - answer_stamp))) AS total_interaction_time,
            COUNT(uuid) AS call_count
        FROM
            cdr
        WHERE
            timestamp >= :start_time
            AND timestamp <= :end_time
            AND answer_stamp IS NOT NULL
            AND end_stamp IS NOT NULL
            AND cc_agent IS NOT NULL
        GROUP BY
            cc_agent;
    """)

    try:
        # Execute the query with UTC timestamps
        result = db.execute(query, {
            'start_time': start_time_utc,
            'end_time': end_time_utc
        }).fetchall()

        processed_result = []
        for row in result:
            agent_name = row[0]  # Accessing the agent name
            total_interaction_time = row[1]  # Total interaction time in seconds
            call_count = row[2]  # Count of calls answered

            # Calculate the average interaction time in seconds
            average_interaction_time = total_interaction_time / call_count if call_count > 0 else 0

            # Create response object, converting seconds to HH:MM:SS format
            if agent_name:  # Ensure agent_name is a valid string before appending
                processed_result.append(
                    schemas.AverageAgentInteractionTimeResponse(
                        name=str(agent_name),
                        average_agent_interaction_time_seconds=seconds_to_hms(int(average_interaction_time))
                    )
                )

        return processed_result

    except Exception as e:
        print(f"Error fetching average agent interaction time: {e}")
        return [{"name": "Error", "average_agent_interaction_time_seconds": "00:00:00"}]