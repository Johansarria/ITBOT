import redis
import json
import logging
import time # ADDED for retry mechanism
import config # Assuming config has REDIS_HOST, REDIS_PORT, REDIS_DB

logger = logging.getLogger(__name__)

# Constants for retry mechanism
MAX_RETRIES = 10
RETRY_DELAY_SECONDS = 5

class MessageQueue:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MessageQueue, cls).__new__(cls)
            cls._instance.redis_client = None # Initialize to None
            for i in range(MAX_RETRIES):
                try:
                    cls._instance.redis_client = redis.StrictRedis(
                        host=config.REDIS_HOST,
                        port=config.REDIS_PORT,
                        db=config.REDIS_DB,
                        decode_responses=True # Decodes responses to UTF-8 strings
                    )
                    cls._instance.redis_client.ping() # Test connection
                    logger.info("Conexión a Redis establecida exitosamente.")
                    break # Connection successful, exit loop
                except redis.exceptions.ConnectionError as e:
                    logger.error(f"Intento {i+1}/{MAX_RETRIES}: Error al conectar a Redis: {e}")
                    if i < MAX_RETRIES - 1:
                        logger.info(f"Reintentando en {RETRY_DELAY_SECONDS} segundos...")
                        time.sleep(RETRY_DELAY_SECONDS)
                    else:
                        logger.critical("Falló la conexión a Redis después de varios reintentos. El bot no funcionará correctamente.")
                        cls._instance.redis_client = None # Ensure client is None on final failure
        return cls._instance

    def publish_decision(self, decision_data: dict):
        if not self.redis_client:
            logger.error("No se pudo publicar la decisión: Conexión a Redis no establecida.")
            return False
        try:
            message = json.dumps(decision_data)
            # Using a list as a queue (LPUSH/BRPOP pattern)
            self.redis_client.lpush(config.REDIS_DECISION_QUEUE_NAME, message)
            logger.info(f"Decisión publicada en la cola '{config.REDIS_DECISION_QUEUE_NAME}': {decision_data.get('type', 'UNKNOWN_DECISION')}")
            return True
        except Exception as e:
            logger.error(f"Error al publicar decisión en Redis: {e}", exc_info=True)
            return False

    def subscribe_decisions(self, callback):
        if not self.redis_client:
            logger.error("No se pudo suscribir a decisiones: Conexión a Redis no establecida.")
            return
        # Using Pub/Sub for real-time notifications, but still using list for queue
        # This part is more complex if you want true Pub/Sub for decisions
        # For simplicity, the worker will poll the list queue.
        # This method would be for a different pattern (e.g., alerts)
        pass

    def get_decision(self, timeout=1):
        if not self.redis_client:
            return None
        try:
            # BRPOP blocks until an element is available or timeout occurs
            # Returns a tuple: (queue_name, message)
            result = self.redis_client.brpop(config.REDIS_DECISION_QUEUE_NAME, timeout=timeout)
            if result: # Check if result is not None
                _, message = result # Now it's safe to unpack
                return json.loads(message)
            return None # Return None if timeout occurred
        except Exception as e:
            logger.error(f"Error al obtener decisión de Redis: {e}", exc_info=True)
            return None

# Initialize the MessageQueue instance (singleton)
mq = MessageQueue()