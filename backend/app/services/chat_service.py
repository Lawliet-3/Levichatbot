from typing import Dict, List, Any
from openai import OpenAI
import os
from ..models.product import Product, ProductQuery
from .rag_service import RAGService
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history = []
        self.current_product = None
        
    def _prepare_context(self, products: List[Dict[str, Any]], query: str) -> str:
        """Prepare product information and conversation context for the LLM."""
        context = ""
        
        # Add recent conversation history
        if self.conversation_history:
            context += "Recent conversation history:\n"
            # Include last 3 messages for context
            recent_messages = self.conversation_history[-3:]
            for msg in recent_messages:
                context += f"{msg['role'].title()}: {msg['content']}\n"
                # If this message mentioned specific products, note them
                if msg.get('products'):
                    for prod in msg['products']:
                        context += f"(Referenced product: {prod['metadata']['product_name']})\n"
            context += "\n"

        # Add current product context if any
        if self.current_product:
            context += f"Currently discussing product: {self.current_product['product_name']}\n\n"

        # Add query analysis
        context += f"Current user query: {query}\n"
        if any(size_word in query.lower() for size_word in ['size', 'waist', 'length', 'fit']):
            context += "Note: User is asking about product sizing/availability.\n"
            if self.current_product:
                context += f"This question likely refers to the current product being discussed: {self.current_product['product_name']}\n"
        
        # Add retrieved products information
        context += "\nRetrieved product information:\n\n"
        for idx, product in enumerate(products, 1):
            prod = product["metadata"]
            context += f"""Product {idx}:
Name: {prod['product_name']}
Price: {prod['sale_price']}
Color: {prod.get('color', 'Not specified')}
Description: {prod['description']}
How it fits: {prod['how_it_fits']}
Composition & Care: {prod['composition_care']}\n\n"""
        
        return context

    def _generate_prompt(self, query: str, context: str) -> str:
        """Generate a prompt for the LLM."""
        return f"""You are a helpful Levi's product assistant. Use the conversation history and product information to provide accurate and contextual responses.

Context:
{context}

Current Question: {query}

Important Instructions:
1. Maintain context from the conversation history
2. If the user asks about sizes/availability, refer to the specific product being discussed
3. Only switch to discussing different products if explicitly requested
4. If the user's question is about a previously discussed product, prioritize that product in your response
5. Be clear and specific about which product you're discussing
6. If the current query is a follow-up question, make sure to maintain context about the previously discussed product
7. For size-related queries, give specific answers about the product being discussed

Please provide a natural, conversational response that directly answers the user's question while maintaining conversation context."""

    def _update_conversation_state(self, role: str, content: str, products: List[Dict] = None):
        """Update conversation history and current product context."""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now(),
            'products': products
        }
        
        self.conversation_history.append(message)
        
        # Keep only last 10 messages
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
            
        # Update current product context
        if products and len(products) > 0:
            self.current_product = products[0]["metadata"]

    def handle_product_query(self, query: str) -> Dict[str, Any]:
        """Handle a product-related query using RAG and LLM."""
        try:
            # Check if this is a direct product request
            show_product_indicators = [
                'show me', 'looking for', 'find me', 'search for', 'want to see',
                'display', "what's the", 'tell me about'
            ]
            
            is_product_request = any(indicator in query.lower() for indicator in show_product_indicators)
            
            # If not a direct product request, handle as a general query without products
            if not is_product_request:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful Levi's product assistant. Provide information without showing specific products unless explicitly asked."},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                response_content = response.choices[0].message.content
                self._update_conversation_state("user", query)
                self._update_conversation_state("assistant", response_content)
                return {
                    "response": response_content,
                    "products": []  # No products for general queries
                }
            
            # For product requests, extract specific product numbers
            import re
            product_numbers = re.findall(r'\d{3}', query)
            
            # Query for specific products
            if product_numbers:
                # Create a specific query for the exact product
                specific_query = f"Levi's {product_numbers[0]}"
                results = self.rag_service.query_products(specific_query)
                
                # Filter results to ensure they match the requested product
                filtered_results = [
                    result for result in results
                    if any(num in result["metadata"]["product_name"] for num in product_numbers)
                ]
                
                results = filtered_results if filtered_results else results
            else:
                # For non-numeric queries, try to match exact product names
                results = self.rag_service.query_products(query)
            
            if not results:
                response = "I couldn't find any products matching your request. Could you please try rephrasing or provide more details?"
                self._update_conversation_state("assistant", response)
                return {
                    "response": response,
                    "products": []
                }
            
            # Prepare context and generate response
            context = self._prepare_context(results, query)
            prompt = self._generate_prompt(query, context)
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful Levi's product assistant. When showing products, only show exactly what was asked for."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            response_content = response.choices[0].message.content
            
            # Only include products in response if it was a direct product request
            self._update_conversation_state("user", query, results if is_product_request else [])
            self._update_conversation_state("assistant", response_content, results if is_product_request else [])
            
            return {
                "response": response_content,
                "products": results if is_product_request else []
            }
            
        except Exception as e:
            logger.error(f"Error handling product query: {str(e)}", exc_info=True)
            return {
                "response": f"I apologize, but I encountered an error while processing your query: {str(e)}",
                "products": []
            }

    def clear_conversation(self):
        """Clear conversation history and current product context."""
        self.conversation_history = []
        self.current_product = None