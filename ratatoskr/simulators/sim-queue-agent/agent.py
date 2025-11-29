import asyncio
import logging
import os
import time
import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sim-queue-agent")

app = FastAPI(title="Heimr.ai Queue Chaos Agent")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_NAME = os.getenv("TOPIC_NAME", "chaos-topic")

class ChaosState:
    flood_active: bool = False
    flood_thread = None
    consumer_lag_ms: int = 0
    poison_pill_active: bool = False

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

@app.post("/control/chaos")
async def set_chaos(config: ChaosConfig):
    """Inject Queue faults."""
    
    # 1. Message Flood (Thundering Herd)
    if config.flood_messages_per_sec is not None:
        if config.flood_messages_per_sec > 0 and not state.flood_active:
            state.flood_active = True
            state.flood_thread = threading.Thread(target=start_flood_loop, args=(config.flood_messages_per_sec,))
            state.flood_thread.start()
        elif config.flood_messages_per_sec == 0 and state.flood_active:
            state.flood_active = False
            if state.flood_thread:
                state.flood_thread.join()

    # 2. Consumer Lag (Simulated by sidecar delay)
    if config.consumer_lag_ms is not None:
        state.consumer_lag_ms = config.consumer_lag_ms
        logger.info(f"Set consumer lag to {state.consumer_lag_ms}ms")

    # 3. Poison Pill
    if config.send_poison_pill:
        producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
        await producer.start()
        try:
            # Send malformed JSON or special header
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
