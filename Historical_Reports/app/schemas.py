# app/schemas.py
from datetime import datetime, time
from pydantic import BaseModel
from typing import Dict, List, Optional


class AgentNameResponse(BaseModel):
    name: str

    class Config:
        from_attributes = True


class AgentNamesResponse(BaseModel):
    agents: List[str]


class TimezoneUpdate(BaseModel):
    user_id: str
    timezone: str


class AgentAnswerRateResponse(BaseModel):
    name: str
    agent_answer_rate: float


class AgentAnswerRateList(BaseModel):
    status: str
    data: List[AgentAnswerRateResponse]


class AgentNonResponse(BaseModel):
    name: str
    no_answer_count: int


class AgentNonResponseList(BaseModel):
    agents: List[AgentNonResponse]


class AgentOnContactTime(BaseModel):
    name: str
    total_on_contact_time_seconds: str  


class AgentOnContactTimeList(BaseModel):
    status: str
    data: List[AgentOnContactTime]
    message: str


class AgentOnlineTime(BaseModel):
    name: str
    online_time: str  


class AgentOnlineTimeList(BaseModel):
    status: str
    data: List[AgentOnlineTime]
    message: str


class NonProductiveTimeResponse(BaseModel):
    name: str
    non_productive_time_seconds: str


class NonProductiveTimeList(BaseModel):
    status: str
    data: List[NonProductiveTimeResponse]


class AgentContactsHandledResponse(BaseModel):
    name: str
    contacts_handled: int


class AgentContactsHandledList(BaseModel):
    status: str
    data: List[AgentContactsHandledResponse]


class AverageAfterContactWorkTimeResponse(BaseModel):
    name: str
    average_after_contact_work_time_seconds: str


class AverageAfterContactWorkTimeList(BaseModel):
    status: str
    data: List[AverageAfterContactWorkTimeResponse]


class AverageAgentInteractionTimeResponse(BaseModel):
    name: str
    average_agent_interaction_time_seconds: str


class AverageAgentInteractionTimeList(BaseModel):
    status: str
    data: List[AverageAgentInteractionTimeResponse]


class AgentMetricsResponse(BaseModel):
    # agents: Optional[UniqueAgentNamesResponse]
    recent_agents: Optional[AgentNamesResponse]
    answer_rates: Optional[AgentAnswerRateList]
    non_responses: Optional[AgentNonResponseList]
    on_contact_times: Optional[AgentOnContactTimeList]
    online_times: Optional[AgentOnlineTimeList]
    non_productive_times: Optional[NonProductiveTimeList]
    contacts_handled: Optional[AgentContactsHandledList]
    after_contact_work_time: Optional[AverageAfterContactWorkTimeList]
    agent_interaction_time: Optional[AverageAgentInteractionTimeList]

    class Config:
        json_schema_extra = {
            "example": {
                # "agents": {
                #     "agents": ["Agent A", "Agent B"]
                # },
                "recent_agents": {
                    "agents": ["Agent A"]
                },
                "answer_rates": {
                    "status": "success",
                    "data": [{
                        "name": "Agent A",
                        "agent_answer_rate": 95.0
                    }]
                },
                "non_responses": {
                    "agents": [{
                        "name": "Agent B",
                        "no_answer_count": 0
                    }]
                },
                "on_contact_times": {
                    "status":
                    "success",
                    "data": [{
                        "name": "Agent A",
                        "total_on_contact_time_seconds": "00:03:00"
                    }],
                    "message":
                    ""
                },
                "online_times": {
                    "status": "success",
                    "data": [{
                        "name": "Agent A",
                        "online_time": "00:10:00"
                    }],
                    "message": ""
                },
                "non_productive_times": {
                    "status":
                    "success",
                    "data": [{
                        "name": "Agent A",
                        "non_productive_time_seconds": 300
                    }]
                },
                "contacts_handled": {
                    "data": [{
                        "name": "Agent A",
                        "contacts_handled": 15
                    }]
                },
                "contacts_on_hold": [{
                    "name": "Agent A",
                    "contacts_on_hold_count": 3
                }],
                "after_contact_work_time": {
                    "status":
                    "success",
                    "data": [{
                        "name":
                        "Agent A",
                        "average_after_contact_work_time_seconds":
                        "00:01:20"
                    }]
                },
                "agent_interaction_time": {
                    "status":
                    "success",
                    "data": [{
                        "name":
                        "Agent A",
                        "average_agent_interaction_time_seconds":
                        "00:06:00"
                    }]
                }
            }
        }


class MetricResponse(BaseModel):
    name: str
    value: float


# --------------------------------------- Queue ----------------------------------->


class UniqueQueueNamesResponse(BaseModel):
    names: List[str]


class AverageHandleTimeResponseForQueues(BaseModel):
    queue: str
    avg_time: float
    avg_time_formatted: str
    total_calls: int


class ServiceLevel60SecondsResponseForQueues(BaseModel):
    queue: str
    service_level_60_seconds: str
    total_calls: int


class ServiceLevel120SecondsResponseForQueues(BaseModel):
    queue: str
    service_level_120_seconds: str
    total_calls: int

class MetricQueueResponseForQueues(BaseModel):
    name: str
    value: float

    class Config:
        from_attributes = True


class AverageAfterContactWorkTimeResponseForQueues(BaseModel):
    queue: str
    avg_time: float
    avg_time_formatted: str


class AverageAgentInteractionTimeResponseForQueues(BaseModel):
    queue: str
    avg_time: float
    avg_time_formatted: str
    total_calls: int


class IncomingContactResponseForQueues(BaseModel):
    total_contacts_handled: int


class IncomingContactListResponseForQueues(BaseModel):
    status: str
    data: List[IncomingContactResponseForQueues]


# class ContactsHandledResponseForQueues(BaseModel):
#     contacts_handled: int


class ContactsHandledResponseForQueues(BaseModel):
    contacts_handled_per_queue: Dict[str, int]


# class ContactsHandledIncomingResponseForQueues(BaseModel):
#     contacts_handled_incoming: int


class ContactsHandledIncomingResponseForQueues(BaseModel):
    contacts_handled_incoming: Dict[str, int]


# class ContactsHandledOutboundResponseForQueues(BaseModel):
#     contacts_handled_outbound: int


class ContactsHandledOutboundResponseForQueues(BaseModel):
    contacts_handled_outbound: Dict[str, int]


class QueueAbandonedContactsForQueues(BaseModel):
    queue: str
    abandoned_count: int


class ContactsAbandonedResponseForQueues(BaseModel):
    queues: List[QueueAbandonedContactsForQueues]

    class Config:
        json_schema_extra = {  # Updated from 'schema_extra'
            "example": {
                "queues": [{
                    "queue": "Support",
                    "abandoned_count": 3
                }, {
                    "queue": "Sales",
                    "abandoned_count": 5
                }]
            }
        }


class AverageQueueAnswerTimePerQueueResponseForQueues(BaseModel):
    average_queue_times: Dict[str, str]


class ContactsQueuedResponseForQueues(BaseModel):
    contacts_queued: Dict[str, int]

    class Config:
        from_attributes = True


class QueueMetricsResponse(BaseModel):
    unique_queue_names: List[str]
    service_levels_60_seconds: List[ServiceLevel60SecondsResponseForQueues]
    service_levels_120_seconds: List[ServiceLevel120SecondsResponseForQueues]
    avg_after_contact_work_time: List[
        AverageAfterContactWorkTimeResponseForQueues]
    avg_interaction_times: List[AverageAgentInteractionTimeResponseForQueues]
    avg_handle_times: List[AverageHandleTimeResponseForQueues]
    contacts_queued: Dict[str, int]
    contacts_handled_incoming: Dict[str, int]
    contacts_handled_outbound: Dict[str, int]
    abandoned_contacts: List[QueueAbandonedContactsForQueues]
    contacts_handled_per_queue: Dict[str, int]


# ------------------------------------------ login/logout  ----------------------------------->


class AgentLoginLogoutEntry(BaseModel):
    agent_name: str
    login_timestamp: datetime
    logout_timestamp: Optional[datetime]
    duration: Optional[time]


class AgentLoginLogoutList(BaseModel):
    status: str
    data: List[AgentLoginLogoutEntry]
    message: Optional[str] = None


# ------------------------------------------ CDR  ----------------------------------->


class CDRReportEntry(BaseModel):
    name: Optional[str]
    queue: Optional[str]
    destination_number: Optional[str]
    caller_id: Optional[str]
    uuid: str
    answer_time: Optional[datetime]
    direction: Optional[str]
    duration: Optional[int]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    billsec: Optional[int]


class CDRReportList(BaseModel):
    status: str
    data: List[CDRReportEntry]
    message: Optional[str] = None

class Agent(BaseModel):
    extension: str
    first_name: str
    last_name: str

class AgentListResponse(BaseModel):
    status: str
    data: List[Agent]
    message: str