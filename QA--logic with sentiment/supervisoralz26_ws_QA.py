#def handle_connection#!/usr/bin/env python3
"""
REALTIME TRANSCRIPT SERVICE - FIXED VERSION
Sends transcripts AND call data with call-end events
"""

import asyncio
import json
import re
import os
import time
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import string
import ssl
from keybert import KeyBERT
import psycopg2  # PostgreSQL support

from vosk import Model, KaldiRecognizer
from websockets import serve
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from kafka import KafkaProducer, KafkaConsumer

import websockets
import threading
from collections import defaultdict

from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")


# ===== ADD THIS BLOCK AT THE TOP =====
import numpy as np
from typing import Dict, List, Tuple, Any

QA_THRESHOLD = 80  # If score below 40 = BAD CALL

# Scoring functions (the "brain")
def calculate_sentiment_score(transcripts):
    customer_transcripts = transcripts.get("Customer", [])
    if not customer_transcripts:
        return 50.0
    customer_sentiments = [t.get("sentiment", {}).get("score", 0) for t in customer_transcripts if t.get("sentiment")]
    if not customer_sentiments:
        return 50.0
    return round(((sum(customer_sentiments) / len(customer_sentiments) + 1) / 2) * 100, 2)

def calculate_resolution_score(transcripts):
    customer_transcripts = transcripts.get("Customer", [])
    if not customer_transcripts:
        return 50.0
    customer_text = " ".join([t.get("text", "").lower() for t in customer_transcripts])
    if "resolved" in customer_text or "fixed" in customer_text or "thank you" in customer_text:
        return 85.0
    return 40.0

def calculate_professionalism_score(transcripts):
    agent_transcripts = transcripts.get("Agent", [])
    if not agent_transcripts:
        return 50.0
    agent_text = " ".join([t.get("text", "").lower() for t in agent_transcripts])
    score = 50
    if "please" in agent_text:
        score += 15
    if "thank you" in agent_text:
        score += 15
    if "sorry" in agent_text or "apolog" in agent_text:
        score += 10
    return min(100.0, float(score))

def calculate_engagement_score(transcripts):
    customer_transcripts = transcripts.get("Customer", [])
    agent_transcripts = transcripts.get("Agent", [])
    if not customer_transcripts or not agent_transcripts:
        return 50.0
    customer_count = len(customer_transcripts)
    agent_count = len(agent_transcripts)
    if customer_count > 0 and agent_count > 0:
        ratio = customer_count / agent_count
        return min(100.0, ratio * 50)
    return 50.0

def calculate_compliance_score(transcripts):
    agent_transcripts = transcripts.get("Agent", [])
    if not agent_transcripts:
        return 50.0
    agent_text = " ".join([t.get("text", "").lower() for t in agent_transcripts])
    if "verify" in agent_text or "confirm" in agent_text or "security" in agent_text:
        return 90.0
    return 50.0

def calculate_efficiency_score(transcripts, call_duration):
    total_messages = sum(len(msgs) for msgs in transcripts.values())
    if total_messages == 0:
        return 50.0
    duration_minutes = call_duration / 60
    if 3 <= duration_minutes <= 8:
        return 100.0
    elif duration_minutes < 3:
        return 60.0
    else:
        return 40.0

def calculate_overall_qa_score(transcripts, call_duration):
    s1 = calculate_sentiment_score(transcripts)
    s2 = calculate_resolution_score(transcripts)
    s3 = calculate_professionalism_score(transcripts)
    s4 = calculate_engagement_score(transcripts)
    s5 = calculate_compliance_score(transcripts)
    s6 = calculate_efficiency_score(transcripts, call_duration)
    
    overall = (s1 * 0.25) + (s2 * 0.20) + (s3 * 0.20) + (s4 * 0.15) + (s5 * 0.10) + (s6 * 0.10)
    
    detailed = {
        "overall_score": round(overall, 2),
        "sentiment_score": s1,
        "resolution_score": s2,
        "professionalism_score": s3,
        "engagement_score": s4,
        "compliance_score": s5,
        "efficiency_score": s6,
    }
    return round(overall, 2), detailed


# global reference to main asyncio loop (populated in main())
EVENT_LOOP = None

SAVE_DIR = "saved_calls"
os.makedirs(SAVE_DIR, exist_ok=True)

PING_INTERVAL = 60
PING_TIMEOUT = 180

# KAFKA CONFIGURATION
KAFKA_BROKER = "10.16.7.62:9092"
TOPIC = "call_transcripts"
SUMMARY_TOPIC = "call_summaries"

# POSTGRESQL DB CONFIG
DB_CONFIG = {
    'host': '10.16.7.95',
    'database': 'freeswitchcore',
    'user': 'dbuser',
    'password': 'Zeniusit123',
    'port': 5432
}

def store_supervisor_alert_to_db(call_id, agent_id, supervisor_id, negative_streak, recent_transcripts):
    """
    Store supervisor alert to PostgreSQL database
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Calculate average customer sentiment from recent transcripts
        customer_sentiments = [
            t.get('sentiment', {}).get('score', 0) 
            for t in recent_transcripts 
            if t.get('speaker') == 'Customer'
        ]
        avg_sentiment = sum(customer_sentiments) / len(customer_sentiments) if customer_sentiments else 0
        
        # Prepare alert metadata
        alert_metadata = {
            "total_transcripts": len(recent_transcripts),
            "customer_messages": len([t for t in recent_transcripts if t.get('speaker') == 'Customer']),
            "agent_messages": len([t for t in recent_transcripts if t.get('speaker') == 'Agent']),
            "call_status": calls.get(call_id, {}).get('status', 'unknown')
        }
        
        insert_query = """
            INSERT INTO supervisor_alerts 
            (call_id, agent_id, supervisor_id, alert_type, negative_streak_count, 
             alert_reason, customer_sentiment_score, recent_transcripts, alert_metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING alert_id
        """
        
        cur.execute(insert_query, (
            call_id,
            agent_id,
            supervisor_id,
            'negative_streak',
            negative_streak,
            f"Customer expressed {negative_streak} consecutive negative statements - immediate supervisor review required",
            round(avg_sentiment, 3),
            json.dumps(recent_transcripts),
            json.dumps(alert_metadata)
        ))
        
        alert_id = cur.fetchone()[0]
        conn.commit()
        
        print(f"[DB] Supervisor alert stored: alert_id={alert_id}, call={call_id}, agent={agent_id}, supervisor={supervisor_id}")
        
        cur.close()
        conn.close()
        
        return alert_id
        
    except Exception as e:
        print(f"[DB ERROR] Failed to store supervisor alert: {e}")
        return None


def acknowledge_supervisor_alert(alert_id, acknowledged_by):
    """
    Mark a supervisor alert as acknowledged
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        update_query = """
            UPDATE supervisor_alerts 
            SET alert_status = 'acknowledged',
                acknowledged_at = CURRENT_TIMESTAMP,
                acknowledged_by = %s
            WHERE alert_id = %s
        """
        
        cur.execute(update_query, (acknowledged_by, alert_id))
        conn.commit()
        
        print(f"[DB] Alert {alert_id} acknowledged by {acknowledged_by}")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"[DB ERROR] Failed to acknowledge alert: {e}")
        return False

def get_supervisor_alerts(supervisor_id=None, status='active', limit=50):
    """
    Retrieve supervisor alerts from database
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        if supervisor_id:
            query = """
                SELECT alert_id, call_id, agent_id, supervisor_id, negative_streak_count,
                       alert_reason, customer_sentiment_score, alert_timestamp, alert_status,
                       recent_transcripts
                FROM supervisor_alerts
                WHERE supervisor_id = %s AND alert_status = %s
                ORDER BY alert_timestamp DESC
                LIMIT %s
            """
            cur.execute(query, (supervisor_id, status, limit))
        else:
            query = """
                SELECT alert_id, call_id, agent_id, supervisor_id, negative_streak_count,
                       alert_reason, customer_sentiment_score, alert_timestamp, alert_status,
                       recent_transcripts
                FROM supervisor_alerts
                WHERE alert_status = %s
                ORDER BY alert_timestamp DESC
                LIMIT %s
            """
            cur.execute(query, (status, limit))
        
        alerts = cur.fetchall()
        cur.close()
        conn.close()
        
        return alerts
        
    except Exception as e:
        print(f"[DB ERROR] Failed to retrieve alerts: {e}")
        return []

# SUPERVISOR SUPPORT
supervisor_connections: dict[str, websockets.WebSocketServerProtocol] = {}
extension_to_calls: defaultdict[str, list[str]] = defaultdict(list)
EXTENSION_TO_SUPERVISOR: dict[str, str] = {}

# Load Vosk Model
VOSK_MODEL_PATH = "/usr/src/vosk/vosk-model-en-in-0.5"
model = Model(VOSK_MODEL_PATH)
print(f"[STARTUP] Vosk model loaded from '{VOSK_MODEL_PATH}'")

# Initialize VADER sentiment analyzer
sentiment_analyzer = SentimentIntensityAnalyzer()
print("[STARTUP] VADER SentimentIntensityAnalyzer loaded")

kw_model = KeyBERT(model="all-MiniLM-L6-v2")
print("[STARTUP] KeyBERT model loaded for keyword extraction")

# ENHANCED KAFKA PRODUCER SETUP
try:
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        request_timeout_ms=120000,
        max_block_ms=120000,
        metadata_max_age_ms=300000,
        connections_max_idle_ms=540000,
        retries=5,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        batch_size=16384,
        linger_ms=5,
        compression_type='gzip',
        acks='all',
        delivery_timeout_ms=180000
    )
    print("[STARTUP] Enhanced Kafka producer initialized")
except Exception as e:
    print(f"[STARTUP] Failed to initialize Kafka producer: {e}")
    producer = None

# Kafka Consumer for summaries
summary_consumer = None

# Enhanced keyword extraction
KEYWORD_BLACKLIST = {
    "hello", "hi", "hey", "thanks", "thank", "you", "good", "morning", "afternoon",
    "evening", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "through", "during", "before", "after",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your",
    "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "having", "do", "does", "did", "doing", "a", "an", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "okay", "ok", "yes", "no",
    "well", "so", "now", "then", "here", "there", "when", "where", "why", "how",
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
    "only", "own", "same", "than", "too", "very", "just"
}

# Track negative streaks for supervisor alert
negative_streaks = defaultdict(int)
NEGATIVE_THRESHOLD = 3

# Enhanced storage structures
calls = {}
transcripts_connections = {}
audio_connections = {}
call_activity = defaultdict(lambda: {"last_seen": time.time(), "message_count": 0})

# Track merged transcript text for live keyphrase extraction
merged_transcripts_text = defaultdict(list)


def leg_label(path: str) -> str:
    """Enhanced leg detection"""
    path_lower = path.lower()
    customer_patterns = [
        r"(?:^|[^a-z0-9])(customer|a_leg|caller|client)(?:[^a-z0-9]|$)",
        r"(?:^|[^a-z0-9])customer(?:[^a-z0-9]|$)",
        r"(?:^|[^a-z0-9])leg_?a(?:[^a-z0-9]|$)"
    ]
    agent_patterns = [
        r"(?:^|[^a-z0-9])(agent|b_leg|representative|rep)(?:[^a-z0-9]|$)",
        r"(?:^|[^a-z0-9])agent(?:[^a-z0-9]|$)",
        r"(?:^|[^a-z0-9])leg_?b(?:[^a-z0-9]|$)"
    ]
    for pattern in customer_patterns:
        if re.search(pattern, path_lower):
            return "Customer"
    for pattern in agent_patterns:
        if re.search(pattern, path_lower):
            return "Agent"
    return "Unknown"


def extract_call_agent(path, metadata=None):
    """Enhanced extraction"""
    call_id = None
    agent_id = None
    if metadata:
        call_id = metadata.get("call_id")
        agent_id = metadata.get("agent_id")
    if not call_id:
        call_patterns = [
            r'call[_-](\w+)',
            r'session[_-](\w+)',
            r'_(\d+\.\d+)',
            r'_(\d{8,})',
            r'/(\w{8,})',
            r'[_-](\w{6,})(?:[_/]|$)'
        ]
        for pattern in call_patterns:
            match = re.search(pattern, path, re.IGNORECASE)
            if match:
                call_id = match.group(1)
                break
    if not call_id:
        path_hash = abs(hash(path.split('?')[0]))
        call_id = f"call_{path_hash % 100000}"
    if not agent_id:
        agent_patterns = [
            r'agent[_-](\w+)',
            r'agentid[_-](\w+)',
            r'user[_-](\w+)',
            r'/(\d{3,5})/',
            r'[_-](\d{3,5})[_-]',
            r'[_-](\d{3,5})(?:[_./]|$)'
        ]
        for pattern in agent_patterns:
            match = re.search(pattern, path, re.IGNORECASE)
            if match:
                agent_id = match.group(1)
                break
    if not agent_id:
        numbers = re.findall(r'\b(\d{3,5})\b', path)
        if numbers:
            agent_id = numbers[0]
    return call_id, agent_id


def analyze_sentiment(text):
    """Sentiment analysis"""
    scores = sentiment_analyzer.polarity_scores(text)
    compound = scores['compound']
    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"
    return {"score": round(compound, 3), "label": label}


def extract_keyphrases(text):
    """Find good keywords using KeyBERT"""
    if not text or len(text.strip()) < 3:
        return []
    try:
        keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words='english',
            use_maxsum=True,
            nr_candidates=20,
            top_n=5
        )
        return [phrase for phrase, score in keywords if len(phrase) > 2]
    except Exception as e:
        print(f"[WARN] Keyword extraction failed: {e}")
        return []


# === FIXED: Normalize supervisor_reference to lowercase ===
def load_supervisor_mapping():
    """
    Query public.directory_search to map agent extensions → supervisor_reference.
    Case-insensitive + space-safe.
    """
    global EXTENSION_TO_SUPERVISOR
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT extension, supervisor_reference 
            FROM public.directory_search 
            WHERE role = 'Agent' 
              AND extension IS NOT NULL 
              AND supervisor_reference IS NOT NULL
              AND supervisor_reference != ''
        """)
        rows = cur.fetchall()
        EXTENSION_TO_SUPERVISOR.clear()

        for ext, sup_ref in rows:
            ext_str = str(ext).strip()
            sup_str = str(sup_ref).strip().lower()   # Normalize to lowercase
            if ext_str and sup_str:
                EXTENSION_TO_SUPERVISOR[ext_str] = sup_str

        print(f"[STARTUP] Loaded {len(EXTENSION_TO_SUPERVISOR)} agent→supervisor mappings from PostgreSQL")
        samples = dict(list(EXTENSION_TO_SUPERVISOR.items())[:4])
        print(f"[DB] Sample mappings: {samples}")
        print(f"[DB DEBUG] Extensions: {list(EXTENSION_TO_SUPERVISOR.keys())}")
        print(f"[DB DEBUG] Supervisors: {list(set(EXTENSION_TO_SUPERVISOR.values()))}")

        if not EXTENSION_TO_SUPERVISOR:
            print("[DB] Warning: No agent→supervisor mappings found!")

        conn.close()

    except Exception as e:
        print(f"[STARTUP] Failed to load supervisor mapping from PostgreSQL: {e}")
        EXTENSION_TO_SUPERVISOR.clear()


def get_supervisor_for_extension(extension: str) -> str | None:
    """Return supervisor_id in lowercase for a given numeric extension."""
    if not extension:
        return None
    return EXTENSION_TO_SUPERVISOR.get(str(extension).strip())


# === BACKGROUND REFRESH TASK ===
async def refresh_supervisor_mapping_periodically():
    """Auto-refresh supervisor mapping every 5 minutes"""
    while True:
        try:
            load_supervisor_mapping()
            print("[REFRESH] Supervisor mapping reloaded from DB")
        except Exception as e:
            print(f"[REFRESH] Failed to reload supervisor mapping: {e}")
        await asyncio.sleep(300)  # 5 minutes


# === SUMMARY CONSUMER FUNCTION ===
def start_summary_consumer():
    """Background Kafka consumer for summaries."""
    try:
        consumer = KafkaConsumer(
            SUMMARY_TOPIC,
            bootstrap_servers=[KAFKA_BROKER],
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='latest',
            group_id='live-summary-listener',
            enable_auto_commit=True,
            session_timeout_ms=30000
        )
        print(f"[KAFKA] Summary consumer started on {SUMMARY_TOPIC}")
        for message in consumer:
            data = message.value
            call_id = data.get("call_id")
            agent_id = data.get("agent_id")
            summary = data.get("summary", "")
            keywords = data.get("keywords", [])
            sentiment = data.get("sentiment_score", 0)
            print(f"[SUMMARY] Received for {call_id} (Agent {agent_id})")
            print(f"Summary: {summary}")
            print(f"Keywords: {keywords}")
            print(f"Sentiment: {sentiment}")
            if agent_id in transcripts_connections and EVENT_LOOP:
                asyncio.run_coroutine_threadsafe(
                    send_to_transcripts_ui(agent_id, "summary", {
                        "call_id": call_id,
                        "summary": summary,
                        "keywords": keywords,
                        "sentiment": sentiment
                    }),
                    EVENT_LOOP
                )
    except Exception as e:
        print(f"[KAFKA] Summary consumer error: {e}")


def save_call_data_async(call_id):
    """Async save"""
    def save_worker():
        if call_id in calls:
            call = calls[call_id]
            agent_id = call.get('agent_id', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            fname = os.path.join(SAVE_DIR, f"{call_id}_{agent_id}_{timestamp}.json")
            try:
                with open(fname, "w", encoding="utf-8") as f:
                    json.dump(call, f, indent=2)
                print(f"[SAVE] Call data saved: {fname}")
            except Exception as e:
                print(f"[ERROR] Failed to save call {call_id}: {e}")
    threading.Thread(target=save_worker, daemon=True).start()


def end_call_automatically(call_id, agent_id, reason="manual"):
    """End call and trigger summary generation - NOW SENDS TRANSCRIPTS TOO"""
    if call_id not in calls:
        print(f"[END] Call {call_id} not found")
        return

    if calls[call_id].get("status") == "ended":
        print(f"[END] Duplicate end event ignored for {call_id}")
        return

    print(f"[END] Ending call {call_id} (reason: {reason})")

    calls[call_id]["status"] = "ended"

        # ===== CALCULATE QA SCORE =====
    print(f"[QA] Analyzing call {call_id}...")
    
    start_time = calls[call_id].get("start_time", time.time())
    end_time = time.time()
    call_duration = end_time - start_time
    
    transcripts = calls[call_id].get("transcripts", {"Agent": [], "Customer": []})
    customer_id = calls[call_id].get("customer_id")
    
    # CALCULATE THE SCORE
    overall_score, detailed_scores = calculate_overall_qa_score(transcripts, call_duration)
    
    print(f"[QA] Score for {call_id}: {overall_score}/100")
    
    # SAVE SCORE TO DATABASE
    try:
        import psycopg2
        conn = psycopg2.connect(host='10.16.7.95', database='freeswitchcore', user='dbuser', password='Zeniusit123', port=5432)
        cur = conn.cursor()
        cur.execute("""
               INSERT INTO qa_score (call_id, agent_id, customer_id, qa_score, message, created_at)
               VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """, (
            call_id, 
            agent_id,
            customer_id,
            overall_score,
            json.dumps(detailed_scores)
        ))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[QA] Score saved to database!")
    except Exception as e:
        print(f"[QA ERROR] {e}")
    
    # IF SCORE IS BAD, SEND ALERT
    if overall_score < QA_THRESHOLD:
        print(f"[QA ALERT] Low score detected: {overall_score}/100")
        
        # Get supervisor
        supervisor_id = get_supervisor_for_extension(agent_id)
        
        # Create alert message
        alert_msg = {
            "type": "supervisor_alert",
            "alert_category": "qa_analysis",
            "call_id": call_id,
            "agent_id": agent_id,
            "qa_score": overall_score,
            "detailed_scores": detailed_scores,
            "reason": f"Low QA score: {overall_score}/100",
            "timestamp": datetime.now(IST).isoformat(),
        }
        
        # Send to supervisor if connected
        if supervisor_id and supervisor_id in supervisor_connections:
            try:
                asyncio.create_task(supervisor_connections[supervisor_id].send(json.dumps(alert_msg)))
                print(f"[QA] Alert sent to supervisor!")
            except:
                pass

    calls[call_id]["end_time"] = datetime.now().isoformat()
    calls[call_id]["end_reason"] = reason

    # Reset negative streak
    negative_streaks.pop(call_id, None)

    save_call_data_async(call_id)

    # Clean extension → calls mapping
    if agent_id and call_id in extension_to_calls.get(agent_id, []):
        extension_to_calls[agent_id].remove(call_id)
        if not extension_to_calls[agent_id]:
            del extension_to_calls[agent_id]

    # SEND CALL-END EVENT WITH TRANSCRIPTS TO KAFKA
    if producer:
        end_event = {
            "call_id": call_id,
            "agent_id": agent_id,
            "customer_id": calls[call_id].get("customer_id"),
            "status": "ended",
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "total_messages": sum(len(transcripts) for transcripts in calls[call_id].get("transcripts", {}).values()),
            "transcripts": calls[call_id].get("transcripts", {}),
        }
        try:
            producer.send(TOPIC, end_event)
            producer.flush()
            print(f"[END] End event sent to Kafka for call {call_id}")
        except Exception as e:
            print(f"[END] Failed to send to Kafka: {e}")

    def cleanup_ended_call():
        time.sleep(5)
        if call_id in calls:
            print(f"[CLEANUP] Removing ended call {call_id}")
            del calls[call_id]
        if call_id in call_activity:
            del call_activity[call_id]
    threading.Thread(target=cleanup_ended_call, daemon=True).start()


async def send_to_transcripts_ui(agent_id, message_type, data):
    """Send to UI"""
    if agent_id in transcripts_connections:
        try:
            message = {
                "type": message_type,
                "timestamp": time.time(),
                **data
            }
            await transcripts_connections[agent_id].send(json.dumps(message))
        except Exception as e:
            print(f"[ERROR] Failed to send to agent {agent_id}: {e}")
            if agent_id in transcripts_connections:
                del transcripts_connections[agent_id]


async def handle_transcripts_connection(websocket, agent_id):
    """Enhanced transcripts connection"""
    print(f"[UI] Transcripts UI connected for agent {agent_id}")

    # ✅ ADD ONLY THIS BLOCK — nothing else changed
    async def ping_loop():
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.ping()
            except:
                return

    asyncio.create_task(ping_loop())
    # ✅ END OF ADDED BLOCK

    transcripts_connections[agent_id] = websocket
    try:
        await send_to_transcripts_ui(agent_id, "status", {
            "status": "connected",
            "message": "Connected to realtime service"
        })
        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get("command") == "end_call":
                    call_id = data.get("callId", "default_call")
                    print(f"[UI] Manual call end request for {call_id}")
                    end_call_automatically(call_id, agent_id, "manual_request")
            except Exception as e:
                print(f"[ERROR] Message handling error: {e}")
    except Exception as e:
        print(f"[ERROR] Connection error for agent {agent_id}: {e}")
    finally:
        if agent_id in transcripts_connections:
            del transcripts_connections[agent_id]
        print(f"[UI] Agent {agent_id} disconnected")



# === FIXED: Normalize supervisor_id and better logging ===
async def handle_supervisor_connection(websocket, supervisor_id: str):
    """Raw WS → store it and push live data for the extensions this supervisor owns."""
    supervisor_id = supervisor_id.strip().lower()  # Normalize
    client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    print(f"[SUPERVISOR] Connecting: '{supervisor_id}' from {client_info}")
    
    supervisor_connections[supervisor_id] = websocket
    print(f"[SUPERVISOR] Active connections: {list(supervisor_connections.keys())}")

    try:
        my_extensions = [ext for ext, sup in EXTENSION_TO_SUPERVISOR.items() if sup == supervisor_id]
        print(f"[SUPERVISOR] '{supervisor_id}' manages: {my_extensions}")

        if not my_extensions:
            print(f"[SUPERVISOR] No extensions found for '{supervisor_id}'")
            print(f"[SUPERVISOR] Available mappings: {dict(list(EXTENSION_TO_SUPERVISOR.items())[:5])}")

        await websocket.send(json.dumps({
            "type": "supervisor_connected",
            "supervisor_id": supervisor_id,
            "timestamp": time.time(),
            "message": f"Connected – monitoring {len(my_extensions)} extensions: {my_extensions}"
        }))

        # Push last 20 utterances
        for ext in my_extensions:
            for call_id in extension_to_calls.get(ext, []):
                if call_id not in calls:
                    continue
                call = calls[call_id]
                for speaker in ("Customer", "Agent"):
                    for tr in call["transcripts"].get(speaker, [])[-20:]:
                        await websocket.send(json.dumps({
                            "type": "transcript",
                            "call_id": call_id,
                            "extension": ext,
                            "speaker": speaker,
                            "final": tr.get("text", ""),
                            "sentiment": tr.get("sentiment", {}),
                            "timestamp": tr.get("timestamp", "")
                        }))

        # Handle commands
        async for message in websocket:
            try:
                data = json.loads(message)
                cmd = data.get("type")
                if cmd == "clear_alerts":
                    print(f"[SUPERVISOR] {supervisor_id} cleared alerts")
                elif cmd == "acknowledge_alert":
                    # **NEW: Handle alert acknowledgment**
                    alert_id = data.get("alert_id")
                    if alert_id:
                        success = await asyncio.to_thread(
                            acknowledge_supervisor_alert,
                            alert_id,
                            supervisor_id
                        )
                        if success:
                            await websocket.send(json.dumps({
                                "type": "alert_acknowledged",
                                "alert_id": alert_id,
                                "timestamp": datetime.now().isoformat()
                            }))
                elif cmd == "end_call":
                    call_id = data.get("call_id")
                    agent_id = data.get("agent_id") or data.get("extension")
                    end_call_automatically(call_id, agent_id, "supervisor_end")
                elif cmd == "generate_summary":
                    call_id = data.get("call_id")
                    agent_id = data.get("agent_id") or data.get("extension")
                    end_call_automatically(call_id, agent_id, "supervisor_summary")
            except Exception as e:
                print(f"[SUPERVISOR] Bad message: {e}")

    except websockets.exceptions.ConnectionClosed:
        print(f"[SUPERVISOR] {supervisor_id} disconnected")
    finally:
        supervisor_connections.pop(supervisor_id, None)
        print(f"[SUPERVISOR] Active after disconnect: {list(supervisor_connections.keys())}")


async def handle_audio_connection(websocket, path):
    """Enhanced audio connection with partial transcript streaming"""
    label = leg_label(path)
    print(f"[AUDIO] New {label} connection: {path}")
    recognizer = KaldiRecognizer(model, 16000)
    call_id, agent_id = extract_call_agent(path)
    audio_connections[path] = {
        "websocket": websocket,
        "label": label,
        "call_id": call_id,
        "agent_id": agent_id,
        "connected_at": time.time()
    }
    customer_id = None

    # Ensure call entry exists
    if call_id and agent_id:
        if call_id not in calls:
            calls[call_id] = {
                "call_id": call_id,
                "agent_id": agent_id,
                "customer_id": customer_id,
                "metadata": {"path": path, "label": label},
                "transcripts": {"Agent": [], "Customer": []},
                "status": "active",
                "start_time": time.time(),
                "last_activity": time.time()
            }
            call_activity[call_id]["last_seen"] = time.time()
            print(f"[CALL] New call initialized: {call_id} (Agent: {agent_id})")
            save_call_data_async(call_id)

    try:
        async for message in websocket:
            if isinstance(message, str):
                try:
                    data = json.loads(message)
                    if "metadata" in data or "config" in data:
                        meta = data.get("metadata", data.get("config", {}))
                        new_call_id, new_agent_id = extract_call_agent(path, meta)
                        incoming_customer_id = meta.get("customer_id")

                        print(f"[METADATA] call_id: {new_call_id}, agent_id: {new_agent_id}, customer_id: {incoming_customer_id}")

                        if new_call_id and new_call_id != call_id:
                            if call_id in calls and new_call_id not in calls:
                                calls[new_call_id] = calls.pop(call_id)
                                if call_id in call_activity:
                                    call_activity[new_call_id] = call_activity.pop(call_id)
                                print(f"[CALL] Migrated call data {call_id} -> {new_call_id}")
                            call_id = new_call_id

                        if new_agent_id and new_agent_id != agent_id:
                            agent_id = new_agent_id
                            if call_id in calls:
                                calls[call_id]["agent_id"] = agent_id
                            print(f"[CALL] Agent ID updated: {agent_id}")

                        if call_id not in calls:
                            calls[call_id] = {
                                "call_id": call_id,
                                "agent_id": agent_id,
                                "customer_id": None,
                                "metadata": meta,
                                "transcripts": {"Agent": [], "Customer": []},
                                "status": "active",
                                "start_time": time.time(),
                                "last_activity": time.time()
                            }
                            call_activity[call_id]["last_seen"] = time.time()

                        if incoming_customer_id:
                            calls[call_id]["customer_id"] = incoming_customer_id
                            print(f"[CALL] Customer ID updated: {incoming_customer_id}")

                        if agent_id and call_id not in extension_to_calls[agent_id]:
                            extension_to_calls[agent_id].append(call_id)

                        calls[call_id].setdefault("metadata", {}).update(meta)
                        calls[call_id]["last_activity"] = time.time()

                    elif "event" in data:
                        event_type = data.get("event")
                        print(f"[AUDIO] Event on {label}: {event_type}")
                        if event_type == "call_end" and call_id:
                            end_call_automatically(call_id, agent_id, f"explicit_call_end_event_from_{label.lower()}")

                except json.JSONDecodeError:
                    text = message.strip()
                    if text and call_id and agent_id:
                        await process_transcript_fast(call_id, agent_id, label, text)

            else:
                # MAIN: Handle audio → partial or final
                if recognizer.AcceptWaveform(message):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").strip()
                    if text and call_id and agent_id:
                        await process_transcript_fast(call_id, agent_id, label, text)
                else:
                    # ✅ PARTIAL transcript streaming
                    partial_json = recognizer.PartialResult()
                    partial_data = json.loads(partial_json)
                    partial_text = partial_data.get("partial", "").strip()
                    if partial_text and call_id and agent_id:
                        partial_message = {
                            "type": "transcript",
                            "agent_id": agent_id,
                            "call_id": call_id,
                            "speaker": label,
                            "final": "",
                            "partial": partial_text,
                            "message_type": "partial",
                            "timestamp": time.time()
                        }
                        if agent_id in transcripts_connections:
                            try:
                                await transcripts_connections[agent_id].send(json.dumps(partial_message))
                            except Exception as e:
                                print(f"[PARTIAL ERROR] Failed to send partial to agent {agent_id}: {e}")

    except Exception as e:
        print(f"[AUDIO] Connection error: {e}")
    finally:
        if path in audio_connections:
            del audio_connections[path]
        print(f"[AUDIO] Connection closed: {label}")


async def process_transcript_fast(call_id, agent_id, label, text):
    """Process transcript and send to Kafka"""
    if call_id not in calls:
        calls[call_id] = {
            "call_id": call_id,
            "agent_id": agent_id,
            "customer_id": None,
            "metadata": {"auto_created": True},
            "transcripts": {"Agent": [], "Customer": []},
            "status": "active",
            "start_time": time.time(),
            "last_activity": time.time()
        }
    
    current_time = time.time()
    call_activity[call_id]["last_seen"] = current_time
    call_activity[call_id]["message_count"] += 1
    calls[call_id]["last_activity"] = current_time
    
    sentiment = analyze_sentiment(text)
    keyphrases = await asyncio.to_thread(extract_keyphrases, text)
    
    merged_transcripts_text[call_id].append(text)
    merged_text = " ".join(merged_transcripts_text[call_id])
    live_keyphrases = await asyncio.to_thread(extract_keyphrases, merged_text)
    
    transcript_entry = {
        "text": text,
        "sentiment": sentiment,
        "keyphrases": keyphrases,
        "timestamp": datetime.now().isoformat(),
        "speaker": label,
        "processing_time": current_time
    }

    # NEGATIVE-STREAK ALERT LOGIC (Customer only)
    if label == "Customer":
        sent_label = sentiment["label"]
        if sent_label == "negative":
            negative_streaks[call_id] = negative_streaks.get(call_id, 0) + 1
        else:
            negative_streaks[call_id] = 0

        if negative_streaks.get(call_id, 0) >= NEGATIVE_THRESHOLD:
            print(f"[ALERT] Negative streak alert for {call_id} (streak: {negative_streaks[call_id]})")

            recent_customer = calls[call_id]["transcripts"]["Customer"][-10:]
            recent_agent = calls[call_id]["transcripts"]["Agent"][-10:]
            recent_trans = sorted(
                recent_customer + recent_agent,
                key=lambda t: datetime.fromisoformat(t["timestamp"]).timestamp() if t.get("timestamp") else 0
            )

            # 1. Light alert to AGENT UI
            agent_alert = {
                "type": "supervisor_alert",
                "call_id": call_id,
                "extension": agent_id,
                "reason": f"Customer said {negative_streaks[call_id]} negative statements in a row – supervisor notified",
                "streak": negative_streaks[call_id],
                "timestamp": datetime.now().isoformat()
            }
            if agent_id in transcripts_connections:
                await send_to_transcripts_ui(agent_id, "supervisor_alert", agent_alert)

            # 2. Get supervisor and store alert in DB
            load_supervisor_mapping()
            supervisor_id = get_supervisor_for_extension(agent_id)
            
            # **NEW: Store alert in database**
            alert_id = await asyncio.to_thread(
                store_supervisor_alert_to_db,
                call_id,
                agent_id,
                supervisor_id,
                negative_streaks[call_id],
                recent_trans
            )

            print(f"[ALERT] Lookup: {agent_id} → {supervisor_id}")
            print(f"[ALERT] Active supervisors: {list(supervisor_connections.keys())}")

            # 3. Send detailed alert to SUPERVISOR
            if supervisor_id and supervisor_id in supervisor_connections:
                sup_alert = {
                    "type": "supervisor_alert",
                    "alert_id": alert_id,  # Include DB alert_id
                    "call_id": call_id,
                    "extension": agent_id,
                    "reason": f"Negative streak ({negative_streaks[call_id]}) detected – review call immediately",
                    "negative_streak": negative_streaks[call_id],
                    "timestamp": datetime.now().isoformat(),
                    "transcripts": [
                        {
                            "speaker": t.get("speaker", "Unknown"),
                            "text": t.get("text", ""),
                            "sentiment": t.get("sentiment", {"label": "neutral", "score": 0}),
                            "timestamp": t.get("timestamp", datetime.now().isoformat())
                        }
                        for t in recent_trans if t.get("text")
                    ]
                }
                await supervisor_connections[supervisor_id].send(json.dumps(sup_alert))
                print(f"[ALERT] Sent to supervisor '{supervisor_id}'")
            else:
                print(f"[ALERT] Supervisor not found or not connected: {supervisor_id}")

    calls[call_id]["transcripts"][label].append(transcript_entry)
    
    print(f"[TRANSCRIPT] {call_id} | {label} ({agent_id})")
    print(f" \"{text}\"")
    print(f" {sentiment['label']} ({sentiment['score']:.2f})")
    print(f" Total msgs: {call_activity[call_id]['message_count']}")
    if live_keyphrases:
         print(f" Live merged keyphrases: {live_keyphrases}")
    print("-" * 80)
    
    # SEND TO KAFKA
    if producer:
        transcript_event = {
            "call_id": call_id,
            "agent_id": agent_id,
            "customer_id": calls[call_id].get("customer_id"),
            "speaker": label,
            "text": text,
            "sentiment": sentiment,
            "keyphrases": keyphrases,
            "timestamp": datetime.now().isoformat(),
            "message_count": call_activity[call_id]["message_count"]
        }
        if live_keyphrases:
           transcript_event["live_keyphrases"] = live_keyphrases
        
        try:
            producer.send(TOPIC, transcript_event)
            print(f"[KAFKA] Sent transcript to {TOPIC}: {call_id}")
        except Exception as e:
            print(f"[KAFKA] Failed to send to Kafka: {e}")
    
    # Send to UI
    if agent_id in transcripts_connections:
        transcript_message = {
            "type": "transcript",
            "agent_id": agent_id,
            "call_id": call_id,
            "speaker": label,
            "final": text,
            "partial": "",
            "message_type": "final",
            "sentiment": sentiment,
            "keyphrases": keyphrases,
            "timestamp": current_time
        }
        if live_keyphrases:
             transcript_message["live_keyphrases"] = live_keyphrases
        
        try:
            await transcripts_connections[agent_id].send(json.dumps(transcript_message))
        except Exception as e:
            print(f"[ERROR] Failed to send to agent {agent_id}: {e}")
            if agent_id in transcripts_connections:
                del transcripts_connections[agent_id]

async def handle_connection(websocket, path):
    client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    print(f"[CONNECTION] New connection from {client_info} on {path}")

    try:
        parsed = urlparse(f"ws://localhost{path}")
        query_params = parse_qs(parsed.query)

        # -----------------------------
        #  TRANSCRIPTS UI CONNECTIONS
        # -----------------------------
        if "/transcripts" in path:

            # 1) Try query parameters first (CORRECT for your React UI)
            agent_id = query_params.get("agentId", [None])[0]
            supervisor_id = query_params.get("supervisorId", [None])[0]

            # 2) If no query params ? fallback to /transcripts/ID
            if not agent_id and not supervisor_id:
                tail = path.replace("/transcripts", "").replace("/", "").lower()

                if tail.startswith("supervisor"):
                    supervisor_id = tail
                elif tail.isdigit():
                    agent_id = tail

            # -------------------------
            #   SUPERVISOR UI
            # -------------------------
            if supervisor_id:
                supervisor_id = supervisor_id.lower()
                print(f"[ROUTER] Supervisor UI detected ? {supervisor_id}")
                await handle_supervisor_connection(websocket, supervisor_id)
                return

            # -------------------------
            #   AGENT UI
            # -------------------------
            if agent_id:
                agent_id = agent_id.lower()
                print(f"[ROUTER] Agent UI detected ? {agent_id}")
                await handle_transcripts_connection(websocket, agent_id)
                return

            print("[ERROR] Missing agentId/supervisorId in WS URL")
            await websocket.close(code=1008, reason="Missing identifiers")
            return

        # -----------------------------
        #  AUDIO LEG ROUTING
        # -----------------------------
        print("[ROUTER] Audio leg detected")
        await handle_audio_connection(websocket, path)

    except Exception as e:
        print(f"[ERROR] handle_connection failed: {e}")
        try:
            await websocket.close()
        except:
            pass



async def cleanup_inactive_calls():
    """Periodic cleanup"""
    while True:
        try:
            current_time = time.time()
            cleanup_candidates = []
            
            for call_id, call in list(calls.items()):
                if call.get("status") != "active":
                    continue
                last_activity = call.get("last_activity", call.get("start_time", current_time))
                inactive_time = current_time - last_activity
                if inactive_time > 300:
                    cleanup_candidates.append((call_id, "inactive_5min"))
            
            for call_id, reason in cleanup_candidates:
                agent_id = calls[call_id].get("agent_id")
                print(f"[CLEANUP] Auto-ending call {call_id}")
                end_call_automatically(call_id, agent_id, f"auto_{reason}")
            
            await asyncio.sleep(60)
        except Exception as e:
            print(f"[ERROR] Cleanup error: {e}")
            await asyncio.sleep(60)


async def main():
    """Main server"""
    global EVENT_LOOP
    
    calls.clear()
    call_activity.clear()
    transcripts_connections.clear()
    audio_connections.clear()
    
    print("[INIT] Cleared stale call memory")
    print("[SERVER] Starting WebSocket server...")
    print("[SERVER] Features:")
    print(" - Real-time transcript processing")
    print(" - Kafka integration (publishing transcripts + call data)")
    print(" - Supervisor alerts (3 negative streaks → agent/supervisor UI)")
    print(" - PostgreSQL agent→supervisor mapping")
    print()
    
    try:
        EVENT_LOOP = asyncio.get_running_loop()
        load_supervisor_mapping()  # Initial load
        cleanup_task = asyncio.create_task(cleanup_inactive_calls())
        refresh_task = asyncio.create_task(refresh_supervisor_mapping_periodically())  # Auto-refresh every 5 min
        
        threading.Thread(target=start_summary_consumer, daemon=True).start()
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile="/usr/src/vosk/Identity.pem",
                                    keyfile="/usr/src/vosk/Identity.pem")
        ssl_context.load_verify_locations(cafile="/usr/src/vosk/SystemManagerCA 3.pem")
 
        async with serve(
            handle_connection,
            "0.0.0.0",
            2700,
            ssl=ssl_context,
            ping_interval=None,
            ping_timeout=None,
            max_size=10**6,
            max_queue=100
        ):
            print("[SERVER] Server running on wss://0.0.0.0:2700")
            print("[SERVER] Ready for real-time call processing")
            await asyncio.Future()
    
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOP] Server stopped")
        
        for call_id, call in list(calls.items()):
            if call.get("status") == "active":
                agent_id = call.get("agent_id")
                print(f"[CLEANUP] Ending active call {call_id}")
                end_call_automatically(call_id, agent_id, "server_shutdown")
        
        if producer:
            producer.flush()
            producer.close()
            print("[CLEANUP] Kafka producer closed")
        
        print("[CLEANUP] Complete")
    except Exception as e:
        print(f"[FATAL] Server error: {e}")
        if producer:
            producer.close()
