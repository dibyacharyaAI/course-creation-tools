import asyncio
import json
import logging
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from typing import Callable, List

logger = logging.getLogger("KafkaClient")

class KafkaClient:
    def __init__(self, bootstrap_servers: str, service_name: str):
        self.bootstrap_servers = bootstrap_servers
        self.service_name = service_name
        self.producer = None
        self.consumer = None
        self.running = False

    async def start_producer(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        retries = 0
        max_retries = 1
        while retries < max_retries:
            try:
                await self.producer.start()
                logger.info(f"Kafka Producer started for {self.service_name}")
                return
            except Exception as e:
                retries += 1
                logger.warning(f"Failed to start Kafka producer (attempt {retries}/{max_retries}): {e}")
                await asyncio.sleep(5)
        
        
        logger.error(f"Could not connect to Kafka after {max_retries} attempts. Continuing without Kafka.")
        self.producer = None
        return

    async def publish(self, topic: str, message: dict):
        if not self.producer:
            logger.warning(f"Producer not started, skipping publish to {topic}")
            return
        try:
            await self.producer.send_and_wait(topic, message)
            logger.info(f"Published to {topic}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")

    async def start_consumer(self, topics: List[str], callback: Callable, group_id: str):
        self.consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest'
        )
        
        retries = 0
        max_retries = 1
        while retries < max_retries:
            try:
                await self.consumer.start()
                break
            except Exception as e:
                retries += 1
                logger.warning(f"Failed to start Kafka consumer (attempt {retries}/{max_retries}): {e}")
                await asyncio.sleep(5)
        
        if retries >= max_retries:
             logger.error(f"Could not connect to Kafka consumer after {max_retries} attempts. Continuing without Kafka consumer.")
             return
        self.running = True
        logger.info(f"Kafka Consumer started for {self.service_name} on {topics}")
        
        try:
            async for msg in self.consumer:
                if not self.running: break
                logger.info(f"Consumed from {msg.topic}: {msg.value}")
                await callback(msg.topic, msg.value)
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            await self.consumer.stop()

    async def stop(self):
        self.running = False
        if self.producer:
            await self.producer.stop()
        if self.consumer:
            await self.consumer.stop()
