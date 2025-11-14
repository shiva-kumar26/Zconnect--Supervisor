# app/main.py
from datetime import datetime, timedelta
import queue
from typing import Dict, List
from fastapi import FastAPI, Depends, HTTPException, Query, logger
from sqlalchemy import text
from sqlalchemy.orm import Session
from app import schemas
from app.crud import agentCrud, cdrCrud, loginlogoutCrud, queueCrud,agentnameCrud
from app import utils
from app.utils import seconds_to_hms
from database import get_db
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db
from .models import Recording
from fastapi.responses import StreamingResponse
from io import BytesIO

app = FastAPI()

# Allow all origins (use with caution, better to specify allowed origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # Or specify allowed origins like ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],  # Or specify allowed methods like ["GET", "POST"]
    allow_headers=["*"],  # Or specify allowed headers
)


# app/main.py
@app.get("/agents-performance/15-minutes-time-interval",
         response_model=schemas.AgentMetricsResponse)
def get_agent_metrics(user_time_zone: str = Query(...),
                      db: Session = Depends(get_db)):
    try:
        # Fetch all necessary data
        recent_agents = agentCrud.get_recent_agent_names_last_15_minutes(
            db, user_time_zone)
        answer_rates = agentCrud.fetch_agent_answer_rate_last_15_minutes(
            db, user_time_zone)
        non_responses = agentCrud.fetch_agent_non_response_last_15_minutes(
            db, user_time_zone)
        on_contact_times = agentCrud.fetch_agent_on_contact_time_last_15_minutes(
            db, user_time_zone)
        online_times = agentCrud.fetch_agent_online_time_last_15_minutes(
            db, user_time_zone)
        non_productive_times = agentCrud.fetch_non_productive_time_last_15_minutes(
            db, user_time_zone)
        contacts_handled = agentCrud.fetch_agent_contacts_handled_last_15_minutes(
            db, user_time_zone)
        average_after_contact_work_time = agentCrud.fetch_average_after_contact_work_time_last_15_minutes(
            db, user_time_zone)
        average_agent_interaction_time = agentCrud.fetch_average_agent_interaction_time_last_15_minutes(
            db, user_time_zone)
        # average_agent_interaction_time = crud.fetch_average_agent_interaction_time_last_15_minutes(
        #     db, user_time_zone)

        # Format the data
        response_data = schemas.AgentMetricsResponse(
            recent_agents=schemas.AgentNamesResponse(agents=recent_agents),
            answer_rates=schemas.AgentAnswerRateList(
                status="success",
                data=[
                    schemas.AgentAnswerRateResponse(name=rate[0],
                                                    agent_answer_rate=float(
                                                        rate[1]))
                    for rate in answer_rates
                ]),
            non_responses=schemas.AgentNonResponseList(agents=[
                schemas.AgentNonResponse(name=row.name,
                                         no_answer_count=row.no_answer_count)
                for row in non_responses
            ]),
            on_contact_times=schemas.AgentOnContactTimeList(
                status="success",
                data=on_contact_times,
                message="" if on_contact_times else
                "No data available for the last 15 minutes."),
            online_times=schemas.AgentOnlineTimeList(status="success",
                                                     data=online_times,
                                                     message=""),
            non_productive_times=schemas.NonProductiveTimeList(
                status="success",
                data=[
                    schemas.NonProductiveTimeResponse(
                        name=row['name'],
                        non_productive_time_seconds=row[
                            'non_productive_time_seconds'])
                    for row in non_productive_times
                ]),
            contacts_handled=schemas.AgentContactsHandledList(
                status="success",
                data=[
                    schemas.AgentContactsHandledResponse(
                        name=row['name'],
                        contacts_handled=row['contacts_handled'])
                    for row in contacts_handled
                ]),
            after_contact_work_time=schemas.AverageAfterContactWorkTimeList(
                status="success",
                data=[
                    schemas.AverageAfterContactWorkTimeResponse(
                        name=row['name'],
                        average_after_contact_work_time_seconds=row[
                            'average_after_contact_work_time_seconds'])
                    for row in average_after_contact_work_time
                ]),
             agent_interaction_time=schemas.AverageAgentInteractionTimeList(
            status="success" if average_agent_interaction_time else "error",
            data=average_agent_interaction_time
        ),)
        return response_data

    except Exception as e:
        import traceback
        print("\n? ERROR IN /agents-performance/15-minutes-time-interval ENDPOINT ?")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# to get the metrics for 30 minutes time interval
@app.get("/agents-performance/30-minutes-time-interval",
         response_model=schemas.AgentMetricsResponse)
def get_agent_metrics(user_time_zone: str = Query(...),
                      db: Session = Depends(get_db)):
    try:
        # Fetch all necessary data
        recent_agents = agentCrud.get_recent_agent_names_last_30_minutes(
            db, user_time_zone)
        answer_rates = agentCrud.fetch_agent_answer_rate_last_30_minutes(
            db, user_time_zone)
        non_responses = agentCrud.fetch_agent_non_response_last_30_minutes(
            db, user_time_zone)
        on_contact_times = agentCrud.fetch_agent_on_contact_time_last_30_minutes(
            db, user_time_zone)
        online_times = agentCrud.fetch_agent_online_time_last_30_minutes(
            db, user_time_zone)
        non_productive_times = agentCrud.fetch_non_productive_time_last_30_minutes(
            db, user_time_zone)
        contacts_handled = agentCrud.fetch_agent_contacts_handled_last_30_minutes(
            db, user_time_zone)
        average_after_contact_work_time = agentCrud.fetch_average_after_contact_work_time_last_30_minutes(
            db, user_time_zone)
        average_agent_interaction_time = agentCrud.fetch_average_agent_interaction_time_last_30_minutes(
            db, user_time_zone)

        # Format the data
        response_data = schemas.AgentMetricsResponse(
            recent_agents=schemas.AgentNamesResponse(agents=recent_agents),
            answer_rates=schemas.AgentAnswerRateList(
                status="success",
                data=[
                    schemas.AgentAnswerRateResponse(name=rate[0],
                                                    agent_answer_rate=float(
                                                        rate[1]))
                    for rate in answer_rates
                ]),
            non_responses=schemas.AgentNonResponseList(agents=[
                schemas.AgentNonResponse(name=row.name,
                                         no_answer_count=row.no_answer_count)
                for row in non_responses
            ]),
            on_contact_times=schemas.AgentOnContactTimeList(
                status="success",
                data=on_contact_times,
                message="" if on_contact_times else
                "No data available for the last 15 minutes."),
            online_times=schemas.AgentOnlineTimeList(status="success",
                                                     data=online_times,
                                                     message=""),
            non_productive_times=schemas.NonProductiveTimeList(
                status="success",
                data=[
                    schemas.NonProductiveTimeResponse(
                        name=row['name'],
                        non_productive_time_seconds=row[
                            'non_productive_time_seconds'])
                    for row in non_productive_times
                ]),
            contacts_handled=schemas.AgentContactsHandledList(
                status="success",
                data=[
                    schemas.AgentContactsHandledResponse(
                        name=row['name'],
                        contacts_handled=row['contacts_handled'])
                    for row in contacts_handled
                ]),
            after_contact_work_time=schemas.AverageAfterContactWorkTimeList(
                status="success",
                data=[
                    schemas.AverageAfterContactWorkTimeResponse(
                        name=row['name'],
                        average_after_contact_work_time_seconds=row[
                            'average_after_contact_work_time_seconds'])
                    for row in average_after_contact_work_time
                ]),
            agent_interaction_time=schemas.AverageAgentInteractionTimeList(
            status="success" if average_agent_interaction_time else "error",
            data=average_agent_interaction_time
        ),)
        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/agents-performance/since_today",
         response_model=schemas.AgentMetricsResponse)
def get_agent_metrics(user_time_zone: str = Query(...),
                      db: Session = Depends(get_db)):
    try:
        # Fetch all necessary data
        recent_agents = agentCrud.get_recent_agent_names_today(db, user_time_zone)
        answer_rates = agentCrud.fetch_agent_answer_rate_today(db, user_time_zone)
        non_responses = agentCrud.fetch_agent_non_response_today(db, user_time_zone)
        on_contact_times = agentCrud.fetch_agent_on_contact_time_today(
            db, user_time_zone)
        online_times = agentCrud.fetch_agent_online_time_today(db, user_time_zone)
        non_productive_times = agentCrud.fetch_non_productive_time_today(
            db, user_time_zone)
        contacts_handled = agentCrud.fetch_agent_contacts_handled_today(
            db, user_time_zone)
        average_after_contact_work_time = agentCrud.fetch_average_after_contact_work_time_today(
            db, user_time_zone)
        average_agent_interaction_time = agentCrud.fetch_average_agent_interaction_time_today(
            db, user_time_zone)

        # Format the data
        response_data = schemas.AgentMetricsResponse(
            recent_agents=schemas.AgentNamesResponse(agents=recent_agents),
            answer_rates=schemas.AgentAnswerRateList(
                status="success",
                data=[
                    schemas.AgentAnswerRateResponse(name=rate[0],
                                                    agent_answer_rate=float(
                                                        rate[1]))
                    for rate in answer_rates
                ]),
            # non_responses=schemas.AgentNonResponseList(agents=[
            #     schemas.AgentNonResponse(name=row.name, no_answer_count=row.no_answer_count)
            #     for row in non_responses if row.name is not None  # Validate name
            # ]),
            non_responses=schemas.AgentNonResponseList(agents=[
                schemas.AgentNonResponse(name=row.name,
                                         no_answer_count=row.no_answer_count)
                for row in non_responses  # No need for extra filtering here
            ]),
            on_contact_times=schemas.AgentOnContactTimeList(
                status="success",
                data=on_contact_times,
                message=""
                if on_contact_times else "No data available today."),
            online_times=schemas.AgentOnlineTimeList(status="success",
                                                     data=online_times,
                                                     message=""),
            non_productive_times=schemas.NonProductiveTimeList(
                status="success",
                data=[
                    schemas.NonProductiveTimeResponse(
                        name=row['name'],
                        non_productive_time_seconds=row[
                            'non_productive_time_seconds'])
                    for row in non_productive_times
                ]),
            contacts_handled=schemas.AgentContactsHandledList(
                status="success",
                data=[
                    schemas.AgentContactsHandledResponse(
                        name=row['name'],
                        contacts_handled=row['contacts_handled'])
                    for row in contacts_handled
                ]),
            after_contact_work_time=schemas.AverageAfterContactWorkTimeList(
                status="success",
                data=[
                    schemas.AverageAfterContactWorkTimeResponse(
                        name=row['name'],
                        average_after_contact_work_time_seconds=row[
                            'average_after_contact_work_time_seconds'])
                    for row in average_after_contact_work_time
                ]),
            agent_interaction_time=schemas.AverageAgentInteractionTimeList(
            status="success" if average_agent_interaction_time else "error",
            data=average_agent_interaction_time
        ))
        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents-performance/date-range",
         response_model=schemas.AgentMetricsResponse)
def get_agent_metrics(
        user_time_zone: str = Query(
            ..., description="User's time zone (e.g., 'UTC')"),
        start_date: str = Query(
            ...,
            description="Start date in ISO format (e.g., '2024-09-01T00:00:00')"
        ),
        end_date: str = Query(
            ...,
            description="End date in ISO format (e.g., '2024-09-01T23:59:59')"
        ),
        db: Session = Depends(get_db)):
    try:
        # Fetch recent agent names
        recent_agents = agentCrud.get_recent_agent_names_for_date_range(
            db, user_time_zone, start_date, end_date)

        # Fetch non-responses
        non_responses = agentCrud.fetch_agent_non_response_for_date_range(
            db, user_time_zone, start_date, end_date)

        # Fetch answer rates
        answer_rates = agentCrud.fetch_agent_answer_rate_for_date_range(
            db, user_time_zone, start_date, end_date)
        formatted_answer_rates = [
            schemas.AgentAnswerRateResponse(name=row[0],
                                            agent_answer_rate=row[1])
            for row in answer_rates
        ]

        # Fetch on-contact time
        contact_times = agentCrud.fetch_agent_on_contact_time_for_date_range(
            db, user_time_zone, start_date, end_date)
        formatted_contact_times = [
            schemas.AgentOnContactTime(name=agent["name"],
                                       total_on_contact_time_seconds=agent[
                                           "total_on_contact_time_seconds"])
            for agent in contact_times
        ]

        # Fetch online time
        online_times = agentCrud.fetch_agent_online_time_for_date_range(
            db, user_time_zone, start_date, end_date)
        formatted_online_times = [
            schemas.AgentOnlineTime(name=agent["name"],
                                    online_time=agent["online_time"])
            for agent in online_times
        ]

        # Fetch non-productive time
        non_productive_times = agentCrud.fetch_non_productive_time_for_date_range(
            db, user_time_zone, start_date, end_date)
        formatted_non_productive_times = [
            schemas.NonProductiveTimeResponse(
                name=agent["name"],
                non_productive_time_seconds=agent[
                    "non_productive_time_seconds"])
            for agent in non_productive_times
        ]

        # Fetch contacts handled
        contacts_handled_data = agentCrud.fetch_agent_contacts_handled_for_date_range(
            db, user_time_zone, start_date, end_date)
        formatted_contacts_handled = [
            schemas.AgentContactsHandledResponse(
                name=agent["name"], contacts_handled=agent["contacts_handled"])
            for agent in contacts_handled_data
        ]
        # Fetch average after contact work time
        average_after_contact_work_time = agentCrud.fetch_average_after_contact_work_time_for_date_range(
            db, user_time_zone, start_date, end_date)

        # Fetch average agent interaction time
        average_agent_interaction_time = agentCrud.fetch_average_agent_interaction_time_for_date_range(
            db, user_time_zone, start_date, end_date)

        # Construct the consolidated response
        response_data = schemas.AgentMetricsResponse(
            recent_agents=schemas.AgentNamesResponse(agents=recent_agents),
            answer_rates=schemas.AgentAnswerRateList(
                status="success", data=formatted_answer_rates),
            non_responses=schemas.AgentNonResponseList(agents=non_responses),
            on_contact_times=schemas.AgentOnContactTimeList(
                status="success", data=formatted_contact_times, message=""),
            online_times=schemas.AgentOnlineTimeList(
                status="success", data=formatted_online_times, message=""),
            non_productive_times=schemas.NonProductiveTimeList(
                status="success", data=formatted_non_productive_times),
            contacts_handled=schemas.AgentContactsHandledList(
                status="success", data=formatted_contacts_handled),
            after_contact_work_time=schemas.AverageAfterContactWorkTimeList(
                status="success",
                data=average_after_contact_work_time,
                message="Data fetched successfully."),
            agent_interaction_time=schemas.AverageAgentInteractionTimeList(
                status="success",
                data=average_agent_interaction_time,
                message="Data fetched successfully."))
        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------      Queue      ------------------------------------------->

@app.get("/queue-metrics/15-minutes-time-interval",
         response_model=schemas.QueueMetricsResponse)
def get_queue_metrics(user_time_zone: str = Query(...),
                      db: Session = Depends(get_db)):
    try:
        # Fetch all necessary data
        unique_queue_names = queueCrud.fetch_unique_queue_names(db, user_time_zone)
        service_levels_60_seconds = queueCrud.fetch_service_level_60_seconds_per_queue_last_15_minutes(
            db, user_time_zone)
        service_levels_120_seconds = queueCrud.fetch_service_level_120_seconds_per_queue_last_15_minutes(
            db, user_time_zone)
        avg_after_contact_work_time = queueCrud.fetch_average_after_contact_work_time_for_queues(
            db, user_time_zone)
        avg_queue_answer_time = queueCrud.fetch_average_queue_answer_time_per_queue(
            db, user_time_zone)
        avg_interaction_times = queueCrud.fetch_average_agent_interaction_time_for_queues(
            db, user_time_zone)
        avg_handle_times = queueCrud.fetch_average_handle_time_for_queues(
            db, user_time_zone)
        contacts_queued = queueCrud.fetch_contacts_queued(db, user_time_zone)
        contacts_handled_per_queue = queueCrud.fetch_contacts_handled_per_queue(
            db, user_time_zone)
        contacts_handled_incoming = queueCrud.fetch_contacts_handled_incoming(
            db, user_time_zone)
        contacts_handled_outbound = queueCrud.fetch_contacts_handled_outbound(
            db, user_time_zone)
        abandoned_contacts = queueCrud.fetch_contacts_abandoned(db, user_time_zone)

        # Format the response data
        response_data = schemas.QueueMetricsResponse(
            unique_queue_names=unique_queue_names,
            service_levels_60_seconds=service_levels_60_seconds,
            service_levels_120_seconds=service_levels_120_seconds,
            avg_after_contact_work_time=avg_after_contact_work_time,
            avg_interaction_times=avg_interaction_times,
            avg_handle_times=avg_handle_times,
            contacts_queued=contacts_queued,
            contacts_handled_per_queue=contacts_handled_per_queue,
            contacts_handled_incoming=contacts_handled_incoming,
            contacts_handled_outbound=contacts_handled_outbound,
            abandoned_contacts=abandoned_contacts,
            average_queue_answer_times=
            avg_queue_answer_time  # Add average_queue_answer_times
        )

        return response_data

    except Exception as e:
        # Handle any errors that may arise
        raise HTTPException(status_code=500,
                            detail=f"Error fetching queue metrics: {str(e)}")


@app.get("/queue-metrics/30-minutes-time-interval",
         response_model=schemas.QueueMetricsResponse)
def get_queue_metrics_for_last_30_minutes(user_time_zone: str = Query(...),
                                          db: Session = Depends(get_db)):
    try:
        # Fetch all necessary data
        unique_queue_names = queueCrud.fetch_unique_queue_names_for_30_minutes(
            db, user_time_zone)
        service_levels_60_seconds = queueCrud.fetch_service_level_60_seconds_per_queue_last_30_minutes(
            db, user_time_zone)
        service_levels_120_seconds = queueCrud.fetch_service_level_120_seconds_per_queue_last_30_minutes(
            db, user_time_zone)
        avg_after_contact_work_time = queueCrud.fetch_average_after_contact_work_time_for_queues_last_30_minutes(
            db, user_time_zone)
        avg_interaction_times = queueCrud.fetch_average_agent_interaction_time_for_queues_last_30_minutes(
            db, user_time_zone)
        avg_handle_times = queueCrud.fetch_average_handle_time_for_queues_last_30_minutes(
            db, user_time_zone)
        contacts_queued = queueCrud.fetch_contacts_queued_last_30_minutes(
            db, user_time_zone)
        contacts_handled_per_queue = queueCrud.fetch_contacts_handled_last_30_minutes_per_queue(
            db, user_time_zone)
        contacts_handled_incoming = queueCrud.fetch_contacts_handled_incoming_last_30_minutes(
            db, user_time_zone)
        contacts_handled_outbound = queueCrud.fetch_contacts_handled_outbound_last_30_minutes(
            db, user_time_zone)
        abandoned_contacts = queueCrud.fetch_contacts_abandoned_last_30_minutes(
            db, user_time_zone)
        avg_queue_answer_time = queueCrud.fetch_average_queue_answer_time_per_queue_last_30_minutes(
            db, user_time_zone)

        # Format the response data
        response_data = {
            "unique_queue_names": unique_queue_names,
            "service_levels_60_seconds": service_levels_60_seconds,
            "service_levels_120_seconds": service_levels_120_seconds,
            "avg_after_contact_work_time": avg_after_contact_work_time,
            "avg_interaction_times": avg_interaction_times,
            "avg_handle_times": avg_handle_times,
            "contacts_queued": contacts_queued,
            "contacts_handled_per_queue": contacts_handled_per_queue,
            "contacts_handled_incoming": contacts_handled_incoming,
            "contacts_handled_outbound": contacts_handled_outbound,
            "abandoned_contacts": abandoned_contacts,
            "avg_queue_answer_time": avg_queue_answer_time
        }

        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/queue-metrics/today", response_model=schemas.QueueMetricsResponse)
def get_queue_metrics_for_Today(user_time_zone: str = Query(...),
                                db: Session = Depends(get_db)):
    try:
        # Fetch all necessary data
        unique_queue_names = queueCrud.fetch_unique_queue_names_for_today(
            db, user_time_zone)
        service_levels_60_seconds = queueCrud.fetch_service_level_60_seconds_per_queue_today(
            db, user_time_zone)
        service_levels_120_seconds = queueCrud.fetch_service_level_120_seconds_per_queue_today(
            db, user_time_zone)
        avg_after_contact_work_time = queueCrud.fetch_average_after_contact_work_time_for_queues_today(
            db, user_time_zone)
        avg_interaction_times = queueCrud.fetch_average_agent_interaction_time_for_queues_today(
            db, user_time_zone)
        avg_handle_times = queueCrud.fetch_average_handle_time_for_queues_today(
            db, user_time_zone)
        contacts_queued = queueCrud.fetch_contacts_queued_today(
            db, user_time_zone)
        contacts_queued = queueCrud.fetch_contacts_queued_today(db, user_time_zone)
        contacts_handled_per_queue = queueCrud.fetch_contacts_handled_today(
            db, user_time_zone)
        contacts_handled_incoming = queueCrud.fetch_contacts_handled_incoming_today(
            db, user_time_zone)
        contacts_handled_outbound = queueCrud.fetch_contacts_handled_outbound_today(
            db, user_time_zone)
        abandoned_contacts = queueCrud.fetch_contacts_abandoned_today(
            db, user_time_zone)
        avg_queue_answer_time = queueCrud.fetch_average_queue_answer_time_per_queue_today(
            db, user_time_zone)

        # Check if contacts_handled_per_queue is None and set to an empty dict if so
        if contacts_handled_per_queue is None:
            contacts_handled_per_queue = {}

        # Format the response data
        response_data = schemas.QueueMetricsResponse(
            unique_queue_names=unique_queue_names,
            service_levels_60_seconds=service_levels_60_seconds,
            service_levels_120_seconds=service_levels_120_seconds,
            avg_after_contact_work_time=avg_after_contact_work_time,
            avg_interaction_times=avg_interaction_times,
            avg_handle_times=avg_handle_times,
            contacts_queued=contacts_queued,
            contacts_handled_per_queue=contacts_handled_per_queue,
            contacts_handled_incoming=contacts_handled_incoming,
            contacts_handled_outbound=contacts_handled_outbound,
            abandoned_contacts=abandoned_contacts,
            avg_queue_answer_time=avg_queue_answer_time)

        return response_data

    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"An error occurred: {str(e)}")


@app.get("/api/queue-metrics/daterange",
         response_model=schemas.QueueMetricsResponse)
async def get_queue_metrics(user_time_zone: str,
                            start_date: str,
                            end_date: str,
                            db: Session = Depends(get_db)):
    # Validate input dates
    try:
        datetime.fromisoformat(start_date)
        datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)."
        )

    try:
        # Fetch all required metrics
        unique_queue_names = queueCrud.fetch_unique_queue_names_for_date_range(
            db, user_time_zone, start_date, end_date)
        service_levels_60_seconds = queueCrud.fetch_service_level_60_seconds_per_queue_for_date_range(
            db, user_time_zone, start_date, end_date)
        service_levels_120_seconds = queueCrud.fetch_service_level_120_seconds_per_queue_for_date_range(
            db, user_time_zone, start_date, end_date)
        avg_after_contact_work_time = queueCrud.fetch_average_after_contact_work_time_for_queues_for_date_range(
            db, user_time_zone, start_date, end_date)
        avg_interaction_times = queueCrud.fetch_average_agent_interaction_time_for_queues_for_date_range(
            db, user_time_zone, start_date, end_date)
        avg_handle_times = queueCrud.fetch_average_handle_time_for_queues_for_date_range(
            db, user_time_zone, start_date, end_date)
        contacts_queued = queueCrud.fetch_contacts_queued_for_date_range(
            db, user_time_zone, start_date, end_date)
        contacts_handled_per_queue = queueCrud.fetch_contacts_handled_for_date_range(
            db, user_time_zone, start_date, end_date)
        contacts_handled_incoming = queueCrud.fetch_contacts_handled_incoming_for_date_range(
            db, user_time_zone, start_date, end_date)
        contacts_handled_outbound = queueCrud.fetch_contacts_handled_outbound_for_date_range(
            db, user_time_zone, start_date, end_date)
        abandoned_contacts = queueCrud.fetch_contacts_abandoned_for_date_range(
            db, user_time_zone, start_date, end_date)
        avg_queue_answer_time = queueCrud.fetch_average_queue_answer_time_per_queue_for_date_range(
            db, user_time_zone, start_date, end_date)
        # Create the response model
        return schemas.QueueMetricsResponse(
            unique_queue_names=unique_queue_names,
            service_levels_60_seconds=service_levels_60_seconds,
            service_levels_120_seconds=service_levels_120_seconds,
            avg_after_contact_work_time=avg_after_contact_work_time,
            avg_interaction_times=avg_interaction_times,
            avg_handle_times=avg_handle_times,
            contacts_queued=contacts_queued,
            contacts_handled_per_queue=contacts_handled_per_queue,
            contacts_handled_incoming=contacts_handled_incoming,
            contacts_handled_outbound=contacts_handled_outbound,
            abandoned_contacts=abandoned_contacts,
            avg_queue_answer_time=avg_queue_answer_time)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------     login/logout      --------------------------------------->


@app.get("/agents-login-logout/today", response_model=schemas.AgentLoginLogoutList)
def get_agent_login_logout_today(user_time_zone: str = Query(...), db: Session = Depends(get_db)):
    try:
        # Fetch the login/logout data for today
        login_logout_data = loginlogoutCrud.fetch_agent_login_logout_today(db, user_time_zone)

        if not login_logout_data:
            return schemas.AgentLoginLogoutList(status="success", data=[], message="No data available for today.")
        
        # Return success message when data is available
        return schemas.AgentLoginLogoutList(status="success", data=login_logout_data, message="Data retrieved successfully.")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/agents-performance/login_logout_custom_range", response_model=schemas.AgentLoginLogoutList)
def get_agent_login_logout_for_date_range(user_time_zone: str = Query(...),
                                          start_date: str = Query(...),
                                          end_date: str = Query(...),
                                          db: Session = Depends(get_db)):
    try:
        # Fetch agent login/logout data for the custom date range
        login_logout_data = loginlogoutCrud.fetch_agent_login_logout_for_date_range(db, user_time_zone, start_date, end_date)

        # Check if there is no data available for the given date range
        if not login_logout_data:
            return schemas.AgentLoginLogoutList(status="success", data=[], message="No data available for the selected date range.")
        
        # Return the response with the retrieved data and a success message
        return schemas.AgentLoginLogoutList(status="success", data=login_logout_data, message="Data retrieved successfully for the selected date range.")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




# ------------------------------------------ CDR Reports ----------------------------------->

@app.get("/cdr-reports/today", response_model=schemas.CDRReportList)
def get_cdr_today(user_time_zone: str = Query(...), db: Session = Depends(get_db)):
    try:
        cdr_data = cdrCrud.fetch_cdr_today(db, user_time_zone)
        if not cdr_data:
            return schemas.CDRReportList(status="success", data=[], message="No CDR data found for today.")
        return schemas.CDRReportList(status="success", data=cdr_data, message="CDR data fetched successfully.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cdr-reports/custom-range", response_model=schemas.CDRReportList)
def get_cdr_custom_range(user_time_zone: str = Query(...),
                         start_date: str = Query(...),
                         end_date: str = Query(...),
                         db: Session = Depends(get_db)):
    try:
        cdr_data = cdrCrud.fetch_cdr_custom_range(db, user_time_zone, start_date, end_date)
        if not cdr_data:
            return schemas.CDRReportList(status="success", data=[], message="No CDR data found for selected date range.")
        return schemas.CDRReportList(status="success", data=cdr_data, message="CDR data fetched successfully.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    

@app.get("/agents", response_model=schemas.AgentListResponse)
def get_all_agents(db: Session = Depends(get_db)):
    try:
        data = agentnameCrud.get_all_agents(db)
        if not data:
            return schemas.AgentListResponse(status="success", data=[], message="No agents found.")
        return schemas.AgentListResponse(status="success", data=data, message="Agents fetched successfully.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/recordings")
def get_recordings(
    agent: str = Query(None),
    caller_id_number: str = Query(None),
    destination_number: str = Query(None),
    queue_name: str = Query(None),
    call_log_id: str = Query(None),   # ? correctly added
    db: Session = Depends(get_db)
):
    query = db.query(Recording)

    if agent:
        query = query.filter(Recording.agent.ilike(f"%{agent}%"))
    if caller_id_number:
        query = query.filter(Recording.caller_id_number.ilike(f"%{caller_id_number}%"))
    if destination_number:
        query = query.filter(Recording.destination_number.ilike(f"%{destination_number}%"))
    if queue_name:
        query = query.filter(Recording.queue_name.ilike(f"%{queue_name}%"))
    if call_log_id:
        query = query.filter(Recording.call_log_id.ilike(f"%{call_log_id}%"))  # ? correct column

    records = query.all()

    output = []
    for r in records:
        output.append({
            "id": r.id,
            "call_log_id": r.call_log_id,
            "caller_id_number": r.caller_id_number,
            "destination_number": r.destination_number,
            "agent": r.agent,
            "duration": r.duration,
            "record_filename": r.record_filename,
            "queue_name": r.queue_name,
            "file_url": f"http://10.16.7.96/recordings/{r.record_filename}" if r.record_filename else None
        })

    return output


@app.get("/api/recordings/play/{record_id}")
def play_recording(record_id: str, db: Session = Depends(get_db)):
    rec = db.query(Recording).filter(Recording.id == record_id).first()

    if not rec or not rec.file_content:
        raise HTTPException(status_code=404, detail="Recording not found")

    audio_bytes = rec.file_content
    file_size = len(audio_bytes)

    return StreamingResponse(
        BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={
            "Content-Length": str(file_size),                # ? REQUIRED
            "Accept-Ranges": "bytes",                        # ? REQUIRED FOR SEEK
            "Content-Disposition": f'attachment; filename="{rec.record_filename}"'  # ? ENABLE DOWNLOAD
        }
    )
