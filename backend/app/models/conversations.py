from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from datetime import datetime

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = None
    referenced_products: List[str] = []  

class ConversationContext(BaseModel):
    current_product_id: Optional[str] = None
    last_query_type: Optional[str] = None  
    product_history: List[str] = []  
    
class ConversationMemory:
    def __init__(self, max_history: int = 10):
        self.messages: List[Message] = []
        self.context: ConversationContext = ConversationContext()
        self.max_history = max_history
    
    def add_message(self, role: str, content: str, referenced_products: List[str] = None):
        """Add a new message to the conversation history."""
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            referenced_products=referenced_products or []
        )
        self.messages.append(message)
        
        # Update context based on referenced products
        if referenced_products:
            self.context.current_product_id = referenced_products[0]
            for product_id in referenced_products:
                if product_id not in self.context.product_history:
                    self.context.product_history.append(product_id)
        
        # Maintain max history
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
    
    def get_recent_context(self, num_messages: int = 3) -> str:
        """Get recent conversation context for the LLM prompt."""
        recent_messages = self.messages[-num_messages:]
        context = ""
        for msg in recent_messages:
            context += f"{msg.role.title()}: {msg.content}\n"
        return context.strip()
    
    def get_current_product(self) -> Optional[str]:
        """Get the currently discussed product ID."""
        return self.context.current_product_id
    
    def get_product_history(self) -> List[str]:
        """Get the list of recently discussed products."""
        return self.context.product_history
    
    def clear(self):
        """Clear the conversation history and context."""
        self.messages = []
        self.context = ConversationContext()

    def update_context(self, query_type: str):
        """Update the context with the current query type."""
        self.context.last_query_type = query_type