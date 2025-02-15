# utils/validators.py
from pydantic import BaseModel, validator
from typing import Optional, List

class UserInput(BaseModel):
    message: str
    context: Optional[dict]

    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty")
        if len(v) > 500:
            raise ValueError("Message too long (max 500 characters)")
        return v.strip()
