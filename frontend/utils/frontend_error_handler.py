# utils/frontend_error_handler.py
import streamlit as st
from typing import Optional, Callable

class FrontendErrorHandler:
    @staticmethod
    def handle_api_error(error: Exception, fallback_message: Optional[str] = None):
        error_message = fallback_message or "An error occurred while processing your request."
        
        if hasattr(error, 'response'):
            try:
                error_data = error.response.json()
                error_message = error_data.get('error', error_message)
                error_id = error_data.get('error_id')
                
                st.error(f"Error: {error_message}")
                if error_id:
                    st.info(f"Error ID: {error_id}")
            except:
                st.error(error_message)
        else:
            st.error(f"Error: {str(error)}")

    @staticmethod
    def with_error_handling(func: Callable):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                FrontendErrorHandler.handle_api_error(e)
        return wrapper