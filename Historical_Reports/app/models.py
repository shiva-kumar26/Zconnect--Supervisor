from sqlalchemy import INTEGER, TIMESTAMP, Column, ForeignKey, Integer, String, Float, DateTime, Time, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Login(Base):
    __tablename__ = 'Login'

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(100), nullable=True)
    agent_status = Column(String(50), nullable=True)
    login_timestamp = Column(TIMESTAMP, nullable=False)
    logout_timestamp = Column(TIMESTAMP, nullable=True)
    duration = Column(Time, nullable=True)

class HistoricalAgent(Base):
    __tablename__ = 'historical_agents_metrics'
    timestamp = Column(TIMESTAMP(timezone=True), primary_key=True, index=True)
    agent_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    instance_id = Column(String)
    uuid = Column(String)
    type = Column(String)
    contact = Column(String)
    status = Column(String)
    state = Column(String)
    max_no_answer = Column(Integer)
    wrap_up_time = Column(Integer)
    reject_delay_time = Column(Integer)
    busy_delay_time = Column(Integer)
    no_answer_delay_time = Column(Integer)
    last_bridge_start = Column(TIMESTAMP(timezone=True))
    last_bridge_end = Column(TIMESTAMP(timezone=True))
    last_offered_call = Column(TIMESTAMP(timezone=True))
    last_status_change = Column(TIMESTAMP(timezone=True))
    no_answer_count = Column(Integer)
    calls_answered = Column(Integer)
    talk_time = Column(Float)
    ready_time = Column(Float)
    external_calls_count = Column(Integer)
    directory_id = Column(Integer)

class HistoricalQueueMetrics(Base):
    __tablename__ = "historical_queue_metrics"
    timestamp = Column(DateTime, primary_key=True)
    queue_id = Column(Integer, primary_key=True)
    name = Column(String)
    strategy = Column(String)
    moh_sound = Column(String)
    record_template = Column(String)
    time_base_score = Column(Integer)
    max_wait_time = Column(Integer)
    max_wait_time_with_no_agent = Column(Integer)
    max_wait_time_with_no_agent_time_reached = Column(Integer)
    tier_rules_apply = Column(String)
    tier_rule_wait_second = Column(Integer)
    tier_rule_wait_multiply_level = Column(Integer)
    tier_rule_no_agent_no_wait = Column(String)
    discard_abandoned_after = Column(Integer)
    abandoned_resume_allowed = Column(String)
    announce_sound = Column(String)
    announce_frequency = Column(Integer)
    calls_answered = Column(Integer)
    calls_abandoned = Column(Integer)


class HistoricalTiersMetrics(Base):
    __tablename__ = "historical_tiers_metrics"
    timestamp = Column(DateTime, primary_key=True)
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer)
    agent = Column(String)
    queue = Column(String)
    state = Column(String)
    level = Column(Integer)
    position = Column(Integer)

    
class CDR(Base):
    __tablename__ = 'cdr'

    local_ip_v4 = Column(String)
    caller_id_name = Column(String)
    caller_id_number = Column(String)
    destination_number = Column(String)
    context = Column(String)
    start_stamp = Column(TIMESTAMP)
    answer_stamp = Column(TIMESTAMP)
    end_stamp = Column(TIMESTAMP)
    duration = Column(INTEGER)
    billsec = Column(INTEGER)
    hangup_cause = Column(String)
    uuid = Column(String, primary_key=True)  # Assuming UUID is the primary key
    bleg_uuid = Column(String)
    accountcode = Column(String)
    read_codec = Column(String)
    write_codec = Column(String)
    sip_hangup_disposition = Column(String)
    ani = Column(String)
    direction = Column(String)
    sip_from_user = Column(String)
    sip_to_user = Column(String)
    sip_from_uri = Column(String)
    sip_call_id = Column(String)
    sip_contact_user = Column(String)
    sip_user_agent = Column(String)
    cc_agent = Column(String)
    cc_queue = Column(String)
    last_sent_callee_id_name = Column(String)
    current_application_data = Column(String)
    answer_epoch = Column(INTEGER)
    bridge_epoch = Column(INTEGER)
    last_hold_epoch = Column(INTEGER)
    progress_epoch = Column(INTEGER)
    end_epoch = Column(INTEGER)
    progresssec = Column(INTEGER)
    answersec = Column(INTEGER)
    waitsec = Column(INTEGER)
    chan_name = Column(String)
    created_time = Column(TIMESTAMP)
    progress_time = Column(TIMESTAMP)
    answered_time = Column(TIMESTAMP)
    timestamp = Column(TIMESTAMP)

    def __repr__(self):
        return f"<CDR(uuid={self.uuid}, caller_id_number={self.caller_id_number})>"
    



class LoginLogout(Base):
    __tablename__ = 'login_logout'

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(100), nullable=False)
    agent_status = Column(String(50), nullable=False)
    login_timestamp = Column(TIMESTAMP, nullable=False)
    logout_timestamp = Column(TIMESTAMP, nullable=True)
    duration = Column(Time, nullable=True)
    role = Column(String(255), nullable=False)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    agent = Column(String)
    domain = Column(String)
    queue = Column(String, nullable=True)
    contact = Column(String)
    status = Column(String, nullable=True)
    state = Column(String, nullable=True)
    max_no_answer = Column(Integer, nullable=True)
    wrap_up_time = Column(Integer, nullable=True)
    reject_delay_time = Column(Integer, nullable=True)
    busy_delay_time = Column(Integer, nullable=True)
    no_answer_delay_time = Column(Integer, nullable=True)
    last_bridge_start = Column(BigInteger, nullable=True)
    last_bridge_end = Column(BigInteger, nullable=True)
    last_offered_call = Column(BigInteger, nullable=True)
    last_status_change = Column(BigInteger, nullable=True)
    no_answer_count = Column(Integer, nullable=True)
    calls_answered = Column(Integer, nullable=True)
    talk_time = Column(Integer, nullable=True)
    ready_time = Column(Integer, nullable=True)
    timeout = Column(Integer, nullable=True)
    position = Column(Integer, nullable=True)


class Directory(Base):
    __tablename__ = "directory"

    directory_id = Column(Integer, primary_key=True, autoincrement=True)
    firstname = Column(String(100), nullable=False)
    lastname = Column(String(100), nullable=False)
    hostname = Column(String(100), nullable=True)
    extension = Column(String(20), nullable=True)
    password = Column(String(100), nullable=False)
    user_id = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)
    supervisor_reference = Column(String(100), nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    call_log_id = Column(String)
    caller_id_number = Column(String)
    destination_number = Column(String)
    agent = Column(String)
    duration = Column(Integer)
    record_filename = Column(String)
    file_content = Column(String)
    queue_name = Column(String)

