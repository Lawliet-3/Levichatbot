from fastapi import HTTPException
from typing import Dict, Any
import logging
import uuid
import requests
import json

logger = logging.getLogger(__name__)

def generate_error_id() -> str:
    return str(uuid.uuid4())

class ErrorHandler:
    @staticmethod
    def handle_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, str]:
        error_id = generate_error_id()
        
        # Log error with context
        logger.error(f"Error ID: {error_id}", exc_info=error, extra=context)

        if isinstance(error, HTTPException):
            return {
                "error": error.detail,
                "error_id": error_id
            }
        
        # Handle different error types
        error_mapping = {
            ValueError: "Invalid input provided",
            requests.exceptions.RequestException: "Network error occurred",
            json.JSONDecodeError: "Invalid data format",
            Exception: "An unexpected error occurred"
        }

        error_message = error_mapping.get(type(error), "An unexpected error occurred")
        
        return {
            "error": error_message,
            "error_id": error_id
        }