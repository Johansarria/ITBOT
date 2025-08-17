import logging
import json
from logging.handlers import RotatingFileHandler

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        if hasattr(record, 'extra'):  # Para logs con contexto adicional
            log_record.update(record.extra)
        return json.dumps(log_record, ensure_ascii=False)

def setup_structured_logger(log_path: str, max_bytes: int = 5_000_000, backup_count: int = 10) -> logging.Logger:
    logger = logging.getLogger("structured_decision")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    formatter = JsonFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
