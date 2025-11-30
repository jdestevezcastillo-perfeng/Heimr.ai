import asyncio
import logging
import os
import time
import threading
import random
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sim-queue-agent")

app = FastAPI(title="Heimr.ai Queue Chaos Agent")

from prometheus_client import make_asgi_app, Gauge, Counter, Histogram
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ========================================
# COMPREHENSIVE KAFKA METRICS
# ========================================

# Producer Metrics
KAFKA_PRODUCER_RECORD_SEND_RATE = Gauge('kafka_producer_record_send_rate', 'Records sent per second', ['topic'])
KAFKA_PRODUCER_BYTE_RATE = Gauge('kafka_producer_byte_rate', 'Bytes sent per second', ['topic'])
KAFKA_PRODUCER_RECORD_ERROR_RATE = Counter('kafka_producer_record_error_total', 'Producer errors', ['topic'])
KAFKA_PRODUCER_REQUEST_LATENCY = Histogram('kafka_producer_request_latency_seconds', 'Producer request latency')

# Consumer Metrics 
KAFKA_CONSUMER_RECORDS_CONSUMED_RATE = Gauge('kafka_consumer_records_consumed_rate', 'Records consumed per sec', ['group', 'topic'])
KAFKA_CONSUMER_BYTES_CONSUMED_RATE = Gauge('kafka_consumer_bytes_consumed_rate', 'Bytes consumed per sec', ['group', 'topic'])
KAFKA_CONSUMER_LAG = Gauge('kafka_consumer_lag', 'Consumer group lag', ['group', 'topic', 'partition'])
KAFKA_CONSUMER_LAG_MAX = Gauge('kafka_consumer_lag_max', 'Max lag across all partitions', ['group', 'topic'])

# Partition Metrics
KAFKA_PARTITION_CURRENT_OFFSET = Gauge('kafka_partition_current_offset', 'Current offset', ['topic', 'partition'])
KAFKA_PARTITION_LOG_END_OFFSET = Gauge('kafka_partition_log_end_offset', 'Log end offset', ['topic', 'partition'])

# Broker Metrics
KAFKA_BROKER_MESSAGES_IN_PER_SEC = Gauge('kafka_broker_messages_in_per_sec', 'Messages in per second')
KAFKA_BROKER_BYTES_IN_PER_SEC = Gauge('kafka_broker_bytes_in_per_sec', 'Bytes in per second')
KAFKA_BROKER_BYTES_OUT_PER_SEC = Gauge('kafka_broker_bytes_out_per_sec', 'Bytes out per second')

# Consumer Group Metrics
KAFKA_CONSUMER_GROUP_REBALANCES = Counter('kafka_consumer_group_rebalances_total', 'Consumer group rebalances', ['group'])
KAFKA_CONSUMER_GROUP_MEMBERS = Gauge('kafka_consumer_group_members', 'Active members in group', ['group'])

# Message Metrics
KAFKA_MESSAGES_TOTAL = Counter('kafka_messages_total', 'Total messages processed', ['topic', 'status'])
KAFKA_MESSAGES_FAILED = Counter('kafka_messages_failed_total', 'Failed message deliveries', ['topic'])

# Offset Commit Metrics
KAFKA_OFFSET_COMMITS = Counter('kafka_offset_commits_total', 'Offset commits', ['group', 'topic'])
KAFKA_OFFSET_COMMIT_LATENCY = Histogram('kafka_offset_commit_latency_seconds', 'Offset commit latency')

# Chaos Metrics (existing)
QUEUE_LEAKED_CONNECTIONS = Gauge('queue_leaked_connections', 'Number of leaked connections')

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_NAME = os.getenv("TOPIC_NAME", "chaos-topic")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "chaos-group")

class ChaosState:
    flood_active: bool = False
    flood_thread = None
    consumer_lag_ms: int = 0
    poison_pill_active: bool = False
    # Simulated state
    current_offset = {0: 10000, 1: 10000, 2: 10000}
    log_end_offset = {0: 10000, 1: 10000, 2: 10000}

state = ChaosState()

class ChaosConfig(BaseModel):
    flood_messages_per_sec: Optional[int] = 0
    consumer_lag_ms: Optional[int] = 0
    send_poison_pill: Optional[bool] = False

async def flood_task(rate_per_sec):
    logger.info(f"Starting flood at {rate_per_sec} msg/sec...")
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    try:
        while state.flood_active:
            start_time = time.time()
            for _ in range(rate_per_sec):
                if not state.flood_active: break
                await producer.send_and_wait(TOPIC_NAME, b"flood_message")
            
            elapsed = time.time() - start_time
            sleep_time = 1.0 - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
    except Exception as e:
        logger.error(f"Flood failed: {e}")
    finally:
        await producer.stop()
        logger.info("Stopped flood.")

def start_flood_loop(rate):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(flood_task(rate))

async def simulate_kafka_activity():
    """Background task that generates realistic Kafka metrics"""
    logger.info("Starting Kafka activity simulation...")
    partitions = [0, 1, 2]
    
    while True:
        # Producer metrics
        send_rate = random.randint(100, 1000) + (5000 if state.flood_active else 0)
        byte_rate = send_rate * random.randint(100, 500)
        
        KAFKA_PRODUCER_RECORD_SEND_RATE.labels(topic=TOPIC_NAME).set(send_rate)
        KAFKA_PRODUCER_BYTE_RATE.labels(topic=TOPIC_NAME).set(byte_rate)
        KAFKA_PRODUCER_REQUEST_LATENCY.observe(random.expovariate(100.0))
        
        # Occasional error
        if random.random() < 0.001:
            KAFKA_PRODUCER_RECORD_ERROR_RATE.labels(topic=TOPIC_NAME).inc()
        
        # Consumer metrics
        consume_rate = random.randint(80, 950)
        consume_bytes = consume_rate * random.randint(100, 500)
        
        KAFKA_CONSUMER_RECORDS_CONSUMED_RATE.labels(group=CONSUMER_GROUP, topic=TOPIC_NAME).set(consume_rate)
        KAFKA_CONSUMER_BYTES_CONSUMED_RATE.labels(group=CONSUMER_GROUP, topic=TOPIC_NAME).set(consume_bytes)
        
        # Partition offsets and lag
        max_lag = 0
        for partition in partitions:
            # Advance offsets
            state.log_end_offset[partition] += send_rate // 3
            state.current_offset[partition] += consume_rate // 3
            
            # Add lag if chaos active
            lag = state.log_end_offset[partition] - state.current_offset[partition]
            if state.consumer_lag_ms > 0:
                lag += state.consumer_lag_ms * 10  # Increase lag
            
            lag = max(0, lag)
            max_lag = max(max_lag, lag)
            
            KAFKA_PARTITION_CURRENT_OFFSET.labels(topic=TOPIC_NAME, partition=str(partition)).set(state.current_offset[partition])
            KAFKA_PARTITION_LOG_END_OFFSET.labels(topic=TOPIC_NAME, partition=str(partition)).set(state.log_end_offset[partition])
            KAFKA_CONSUMER_LAG.labels(group=CONSUMER_GROUP, topic=TOPIC_NAME, partition=str(partition)).set(lag)
        
        KAFKA_CONSUMER_LAG_MAX.labels(group=CONSUMER_GROUP, topic=TOPIC_NAME).set(max_lag)
        
        # Broker metrics
        KAFKA_BROKER_MESSAGES_IN_PER_SEC.set(send_rate)
        KAFKA_BROKER_BYTES_IN_PER_SEC.set(byte_rate)
        KAFKA_BROKER_BYTES_OUT_PER_SEC.set(consume_bytes)
        
        # Consumer group metrics
        KAFKA_CONSUMER_GROUP_MEMBERS.labels(group=CONSUMER_GROUP).set(3)  # 3 consumers
        
        # Messages
        KAFKA_MESSAGES_TOTAL.labels(topic=TOPIC_NAME, status='success').inc(send_rate)
        
        # Occasional failure
        if random.random() < 0.001:
            KAFKA_MESSAGES_FAILED.labels(topic=TOPIC_NAME).inc()
        
        # Offset commits  
        if random.random() < 0.1:
            KAFKA_OFFSET_COMMITS.labels(group=CONSUMER_GROUP, topic=TOPIC_NAME).inc()
            KAFKA_OFFSET_COMMIT_LATENCY.observe(random.expovariate(100.0))
        
        # Occasional rebalance
        if random.random() < 0.001:
            KAFKA_CONSUMER_GROUP_REBALANCES.labels(group=CONSUMER_GROUP).inc()
            logger.info("Simulated consumer group rebalance")
        
        await asyncio.sleep(1.0)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulate_kafka_activity())

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Tie metrics to actual HTTP traffic"""
    if request.url.path not in ["/metrics", "/health"]:
        # Spike activity on requests
        KAFKA_PRODUCER_RECORD_SEND_RATE.labels(topic=TOPIC_NAME).inc(10)
    
    response = await call_next(request)
    return response

@app.post("/control/chaos")
async def set_chaos(config: ChaosConfig):
    """Inject Queue faults."""
    
    # Message Flood (Thundering Herd)
    if config.flood_messages_per_sec is not None:
        if config.flood_messages_per_sec > 0 and not state.flood_active:
            state.flood_active = True
            state.flood_thread = threading.Thread(target=start_flood_loop, args=(config.flood_messages_per_sec,))
            state.flood_thread.start()
        elif config.flood_messages_per_sec == 0 and state.flood_active:
            state.flood_active = False
            if state.flood_thread:
                state.flood_thread.join()

    # Consumer Lag
    if config.consumer_lag_ms is not None:
        state.consumer_lag_ms = config.consumer_lag_ms
        logger.info(f"Set consumer lag to {state.consumer_lag_ms}ms")

    # Poison Pill
    if config.send_poison_pill:
        producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
        await producer.start()
        try:
            await producer.send_and_wait(TOPIC_NAME, b"POISON_PILL_DATA")
            logger.info("Sent Poison Pill")
        finally:
            await producer.stop()

    return {"status": "updated", "state": {
        "flood_active": state.flood_active,
        "consumer_lag_ms": state.consumer_lag_ms
    }}

@app.post("/control/reset")
async def reset_chaos():
    state.flood_active = False
    state.consumer_lag_ms = 0
    if state.flood_thread: state.flood_thread.join()
    return {"status": "reset"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
