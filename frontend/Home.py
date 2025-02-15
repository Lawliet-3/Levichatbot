from typing import Dict, List, Any
import streamlit as st
import requests
import uuid
from datetime import datetime
import pandas as pd

class ChatUI:
    def __init__(self):
        self.API_URL = "http://localhost:8000"
        
        # Initialize session state
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
            
        if "survey_active" not in st.session_state:
            st.session_state.survey_active = False
            
        if "current_question" not in st.session_state:
            st.session_state.current_question = None
            
        if "survey_progress" not in st.session_state:
            st.session_state.survey_progress = None
            
        if "current_survey_id" not in st.session_state:
            st.session_state.current_survey_id = None
            
        if "last_interaction_time" not in st.session_state:
            st.session_state.last_interaction_time = datetime.now()
            
        if "messages_since_prompt" not in st.session_state:
            st.session_state.messages_since_prompt = 0

        # Get surveys on initialization
        try:
            response = requests.get(f"{self.API_URL}/api/surveys")
            self.surveys = response.json() if response.status_code == 200 else []
        except:
            self.surveys = []

    def should_prompt_survey(self):
        """Check if we should prompt for survey"""
        if st.session_state.survey_active:
            return False
            
        # After 5 messages
        if st.session_state.messages_since_prompt >= 5:
            return True
            
        # After 5 minutes of inactivity
        time_since_last = datetime.now() - st.session_state.last_interaction_time
        if time_since_last.seconds >= 10:  # 5 minutes
            return True
            
        return False

    def display_survey_progress(self):
        """Display survey progress bar"""
        if st.session_state.survey_progress:
            progress = st.session_state.survey_progress
            total = progress["total"]
            answered = progress["answered"]
            
            if not progress["is_final"]:
                st.progress(answered / total if total > 0 else 0)
                st.write(f"Question {answered + 1} of {total}")
            else:
                st.write("Final Feedback")

    def display_product(self, product: Dict):
        """Display product information in a formatted card."""
        # If product comes from RAG service, extract the metadata
        if isinstance(product, dict) and "metadata" in product:
            product = product["metadata"]

        with st.container():
            col1, col2 = st.columns([2, 3])
            
            with col1:
                # Handle images with proper error checking
                images_field = product.get("images", "")
                if images_field and not pd.isna(images_field):
                    # Parse semicolon-separated URLs and filter out empty/invalid ones
                    image_urls = [
                        url.strip() 
                        for url in images_field.split(";") 
                        if url.strip() and url.strip().lower() not in ['n/a', 'nan', '']
                    ]
                    
                    if image_urls:
                        # Display the first image
                        try:
                            st.image(image_urls[0], use_container_width=True)  # Changed from use_column_width
                            
                            # Show more images button if there are additional images
                            if len(image_urls) > 1:
                                with st.expander("Show More Images"):
                                    for url in image_urls[1:]:
                                        st.image(url, use_container_width=True)  # Changed from use_column_width
                        except Exception as e:
                            st.error(f"Error loading image: {str(e)}")
                    else:
                        st.info("No product images available")
                else:
                    st.info("No product images available")
            
            with col2:
                # Product name with fallback
                product_name = product.get("product_name")
                if product_name and not pd.isna(product_name):
                    st.subheader(product_name)
                else:
                    st.subheader("Product Name Not Available")
                
                # Price with fallback
                price = product.get("sale_price")
                if price and not pd.isna(price):
                    st.write(f"💰 Price: {price}")
                else:
                    st.write("💰 Price: Not available")
                
                # Color with fallback
                color = product.get("color")
                if color and not pd.isna(color):
                    if isinstance(color, list):
                        st.write(f"🎨 Color: {', '.join(color)}")
                    else:
                        st.write(f"🎨 Color: {color}")
                
                # Description
                description = product.get("description")
                if description and not pd.isna(description):
                    with st.expander("📝 Description"):
                        st.write(description)
                
                # How it fits
                how_it_fits = product.get("how_it_fits")
                if how_it_fits and not pd.isna(how_it_fits):
                    with st.expander("👕 How it fits"):
                        for fit in how_it_fits.split(";"):
                            if fit.strip() and not pd.isna(fit):
                                st.write(f"• {fit.strip()}")
                
                # Composition & Care
                composition_care = product.get("composition_care")
                if composition_care and not pd.isna(composition_care):
                    with st.expander("🧵 Composition & Care"):
                        for care in composition_care.split(";"):
                            if care.strip() and not pd.isna(care):
                                st.write(f"• {care.strip()}")
                            
    def handle_survey_question(self, question: Dict):
        """Display and handle survey questions."""
        st.write("---")
        st.write("📋 Survey")
        
        # Display progress
        self.display_survey_progress()
        
        st.write(question["text"])
        answer = None
        
        if question["type"] == "scale":
            scale_range = question["scale_range"]
            answer = st.slider(
                "",
                min_value=scale_range[0],
                max_value=scale_range[1],
                value=scale_range[0]
            )
        
        elif question["type"] == "multiple_choice":
            answer = st.selectbox("", question["options"], key=f"survey_q_{question['id']}")
        
        elif question["type"] == "text":
            answer = st.text_area("", key=f"survey_q_{question['id']}")
        
        elif question["type"] == "voice":
            col1, col2 = st.columns([3, 1])
            with col1:
                answer = st.text_area("Type your response:", key=f"survey_q_{question['id']}")
            with col2:
                st.write("🎤 Voice recording:")
                if st.button("Start Recording"):
                    st.info("Voice recording feature coming soon!")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if answer:
                if st.button("Submit"):
                    try:
                        response = requests.post(
                            f"{self.API_URL}/api/survey/answer",
                            json={
                                "survey_id": st.session_state.current_survey_id,
                                "user_id": st.session_state.session_id,
                                "answer": {
                                    "question_id": question["id"],
                                    "value": answer
                                }
                            }
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result["completed"]:
                                st.session_state.survey_active = False
                                st.session_state.current_question = None
                                st.session_state.survey_progress = None
                                st.session_state.messages_since_prompt = 0
                                st.session_state.last_interaction_time = datetime.now()
                                st.success("Thank you for completing the survey!")
                                st.rerun()
                            else:
                                st.session_state.current_question = result["next_question"]
                                st.session_state.survey_progress = result["progress"]
                                st.rerun()
                        else:
                            st.error(f"Error submitting answer: {response.text}")
                    except Exception as e:
                        st.error(f"Error submitting answer: {str(e)}")
        
        with col2:
            if not question.get("is_final", False):  # Don't show skip for final question
                if st.button("Skip"):
                    if "current_question" in st.session_state:
                        st.session_state.current_question = None
                    st.session_state.survey_active = False
                    st.session_state.messages_since_prompt = 0
                    st.session_state.last_interaction_time = datetime.now()
                    st.rerun()

    def start_survey(self):
        """Start the survey process."""
        try:
            # First get the current survey
            survey_response = requests.get(f"{self.API_URL}/api/surveys")
            if survey_response.status_code != 200:
                st.error("Error getting survey configuration")
                return
                
            surveys = survey_response.json()
            if not surveys:
                st.error("No survey available")
                return
                
            # Get the default survey (first one)
            default_survey = surveys[0]
            st.session_state.current_survey_id = default_survey["id"]
            
            # Start the survey session
            response = requests.post(
                f"{self.API_URL}/api/survey/start",
                json={
                    "survey_id": st.session_state.current_survey_id,
                    "user_id": st.session_state.session_id,
                    "conversation_id": st.session_state.session_id  # Added conversation_id
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                st.session_state.survey_active = True
                st.session_state.current_question = result.get("current_question")
                st.session_state.survey_progress = result.get("progress")
                st.session_state.messages_since_prompt = 0
                st.rerun()
            else:
                st.error(f"Error starting survey: {response.text}")
                st.session_state.survey_active = False
        except Exception as e:
            st.error(f"Error starting survey: {str(e)}")
            st.session_state.survey_active = False

    def display_chat_interface(self):
        """Display the main chat interface."""
        st.title("Levi's Product Assistant")
        
        # If no messages yet, show recommended questions
        if not st.session_state.messages:
            st.write("👋 Welcome! Here are some questions you can ask:")
            recommended_questions = [
                "Tell me about 501 original jeans",
                "What denim jackets do you have?",
                "Show me some slim fit jeans",
                "What's the price of Levi's 511?",
                "Do you have any black jeans?",
                "Can you recommend comfortable jeans for daily wear?"
            ]
            
            # Create two columns for better layout
            col1, col2 = st.columns(2)
            for idx, question in enumerate(recommended_questions):
                # Alternate between columns
                with col1 if idx % 2 == 0 else col2:
                    if st.button(f"💬 {question}", use_container_width=True):
                        st.session_state.messages.append({"role": "user", "content": question})
                        self.process_message(question)
            
            # Add a separator between recommendations and chat
            st.write("---")
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if "products" in message and message["products"]:
                    for product in message["products"]:
                        self.display_product(product)
        
        # Display current survey question if active
        if st.session_state.survey_active and st.session_state.current_question:
            self.handle_survey_question(st.session_state.current_question)
        # Check if we should prompt for survey
        elif self.should_prompt_survey() and not st.session_state.get("survey_declined", False):
            with st.chat_message("assistant"):
                st.write("Would you mind taking a quick survey about your experience with our chatbot?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Sure, I'll take the survey"):
                        st.session_state.survey_active = True
                        self.start_survey()
                with col2:
                    if st.button("Maybe later"):
                        st.session_state.survey_declined = True
                        st.session_state.last_interaction_time = datetime.now()
                        st.session_state.messages_since_prompt = 0
                        st.rerun()
        
        # Reset survey_declined after some time
        if st.session_state.get("survey_declined", False):
            time_since_decline = datetime.now() - st.session_state.get("last_decline_time", datetime.now())
            if time_since_decline.total_seconds() > 300:  # 5 minutes
                st.session_state.survey_declined = False
        
        # Chat input
        if prompt := st.chat_input("Ask about Levi's products..."):
            st.session_state.last_interaction_time = datetime.now()
            st.session_state.messages_since_prompt += 1
            st.session_state.messages.append({"role": "user", "content": prompt})
            self.process_message(prompt)
    
    def process_message(self, message: str):
        """Process a chat message and get response"""
        try:
            response = requests.post(
                f"{self.API_URL}/api/chat/query",
                json={"query": message, "session_id": st.session_state.session_id}
            )
            
            if response.status_code == 200:
                result = response.json()
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["response"],
                    "products": result.get("products", [])
                })
                st.rerun()
            else:
                st.error(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Error communicating with server: {str(e)}")

class SurveyAdminUI:
    def __init__(self):
        self.API_URL = "http://localhost:8000"
        self.surveys = None  # Will store surveys data
        
        # Initialize session state for editing
        if "editing_question" not in st.session_state:
            st.session_state.editing_question = None
        if "current_conditions" not in st.session_state:
            st.session_state.current_conditions = {}
            
    def _get_surveys(self):
        """Fetch surveys from the API"""
        try:
            response = requests.get(f"{self.API_URL}/api/surveys")
            if response.status_code == 200:
                self.surveys = response.json()
            else:
                st.error("Failed to fetch surveys")
        except Exception as e:
            st.error(f"Error fetching surveys: {str(e)}")

    def _display_condition_editor(self, previous_questions: list, question_id: str):
        """Display the condition editor interface"""
        st.markdown("""
        **How Conditions Work:**
        - Conditions determine when this question should be shown to users
        - Multiple conditions are combined with AND logic (all must be true)
        - Available operators depend on the question type:
            - Scale questions: equals, greater_than, less_than
            - Multiple choice: equals
            - Text questions: equals, contains
        """)
        
        st.write("Define conditions:")
        
        # Initialize conditions if not present in session state
        if question_id not in st.session_state.current_conditions:
            st.session_state.current_conditions[question_id] = []
        
        # Get conditions for this specific question
        conditions = st.session_state.current_conditions[question_id]
        
        # Make sure conditions is a list
        if conditions is None:
            conditions = []
            st.session_state.current_conditions[question_id] = conditions
        
        # Display existing conditions
        for i, condition in enumerate(conditions):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 3, 1])
                
                with col1:
                    prev_q = st.selectbox(
                        "If Question",
                        previous_questions,
                        key=f"cond_q_{question_id}_{i}",
                        format_func=lambda x: f"Q{x['order'] + 1}: {x['text'][:50]}...",
                        index=next(
                            (idx for idx, q in enumerate(previous_questions) 
                            if q["id"] == condition.get("question_id")),
                            0
                        ) if previous_questions else 0
                    )
                
                with col2:
                    available_operators = ["equals"]
                    if prev_q["type"] == "scale":
                        available_operators.extend(["greater_than", "less_than"])
                    elif prev_q["type"] == "text":
                        available_operators.append("contains")
                    
                    operator = st.selectbox(
                        "Operator",
                        available_operators,
                        key=f"cond_op_{question_id}_{i}",
                        index=available_operators.index(condition.get("operator", "equals"))
                    )
                
                with col3:
                    if prev_q["type"] == "scale":
                        # Set default value to minimum of scale range if no value exists
                        default_value = prev_q["scale_range"][0]
                        try:
                            if condition.get("value") is not None:
                                default_value = int(condition["value"])
                        except (ValueError, TypeError):
                            pass
                            
                        value = st.number_input(
                            "Value",
                            min_value=prev_q["scale_range"][0],
                            max_value=prev_q["scale_range"][1],
                            value=default_value,
                            key=f"cond_val_{question_id}_{i}"
                        )
                    elif prev_q["type"] == "multiple_choice":
                        # Set default value to first option if no value exists or value not in options
                        default_index = 0
                        if condition.get("value") in prev_q["options"]:
                            default_index = prev_q["options"].index(condition["value"])
                            
                        value = st.selectbox(
                            "Value",
                            prev_q["options"],
                            key=f"cond_val_{question_id}_{i}",
                            index=default_index
                        )
                    else:
                        value = st.text_input(
                            "Value",
                            value=condition.get("value", ""),
                            key=f"cond_val_{question_id}_{i}"
                        )
                
                with col4:
                    if st.button("❌", key=f"del_cond_{question_id}_{i}"):
                        conditions.pop(i)
                        st.session_state.current_conditions[question_id] = conditions
                        st.rerun()
                
                # Update condition
                conditions[i] = {
                    "question_id": prev_q["id"],
                    "operator": operator,
                    "value": value
                }
        
        # Add new condition button
        if st.button("Add Another Condition", key=f"add_cond_{question_id}"):
            if previous_questions:
                # Initialize new condition with default values
                default_question = previous_questions[0]
                default_value = default_question["scale_range"][0] if default_question["type"] == "scale" else (
                    default_question["options"][0] if default_question["type"] == "multiple_choice" else ""
                )
                
                conditions.append({
                    "question_id": default_question["id"],
                    "operator": "equals",
                    "value": default_value
                })
                st.session_state.current_conditions[question_id] = conditions
                st.rerun()
            else:
                st.warning("No previous questions available for conditions")

    def _display_question_editor(self, question: dict, previous_questions: list):
        """Display editor interface for an existing question"""
        # Make question text editable
        question["text"] = st.text_area(
            "Question Text",
            value=question["text"],
            key=f"text_{question['id']}"
        )
        
        # Basic info
        st.write(f"**Type:** {question['type']}")
        
        if question["type"] == "scale":
            col1, col2 = st.columns(2)
            with col1:
                min_val = st.number_input(
                    "Min Value",
                    value=question["scale_range"][0],
                    key=f"min_{question['id']}"
                )
            with col2:
                max_val = st.number_input(
                    "Max Value",
                    value=question["scale_range"][1],
                    key=f"max_{question['id']}"
                )
            question["scale_range"] = (min_val, max_val)
            
        elif question["type"] == "multiple_choice":
            st.write("**Options:**")
            # Convert options to string for editing
            current_options = "\n".join(question["options"])
            new_options = st.text_area(
                "Options (one per line)",
                value=current_options,
                key=f"options_{question['id']}"
            )
            # Update options in question
            question["options"] = [opt.strip() for opt in new_options.split("\n") if opt.strip()]
        
        # Condition editor toggle
        show_conditions = st.checkbox(
            "Edit Conditions",
            key=f"show_cond_{question['id']}"
        )
        
        if show_conditions:
            if not previous_questions:
                st.info("No previous questions available for conditions")
            else:
                # Initialize conditions for this specific question
                if question["id"] not in st.session_state.current_conditions:
                    st.session_state.current_conditions[question["id"]] = question.get("conditions", [])
                    
                self._display_condition_editor(previous_questions, question["id"])
        
        # Update and delete buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Update", key=f"update_{question['id']}"):
                if self._update_question(self.surveys[0]["id"], question):
                    st.success("Question updated successfully!")
                    st.rerun()
        
        with col2:
            if st.button("Delete", key=f"delete_{question['id']}"):
                try:
                    response = requests.delete(
                        f"{self.API_URL}/api/surveys/{self.surveys[0]['id']}/questions/{question['id']}"
                    )
                    if response.status_code == 200:
                        st.success("Question deleted successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error deleting question: {response.text}")
                except Exception as e:
                    st.error(f"Error deleting question: {str(e)}")

    def display_survey_admin(self):
        """Display the survey admin interface"""
        st.title("Survey Configuration")
        
        # Fetch surveys if needed
        if self.surveys is None:
            self._get_surveys()
            
        if not self.surveys:
            st.error("No surveys available")
            return

        # Add New Question Section
        with st.expander("➕ Add New Question", expanded=not bool(self.surveys[0].get("questions"))):
            with st.form("new_question_form"):
                st.subheader("Add New Question")
                
                # Question text
                question_text = st.text_area("Question Text", placeholder="Enter your question here...")
                
                # Question type selection
                col1, col2 = st.columns(2)
                with col1:
                    question_type = st.selectbox(
                        "Question Type",
                        ["scale", "multiple_choice", "text", "voice"]
                    )
                with col2:
                    is_final = st.checkbox(
                        "Final Question",
                        help="This will be the last question (open-ended feedback)"
                    )
                
                # Type-specific options
                if question_type == "scale":
                    col1, col2 = st.columns(2)
                    with col1:
                        min_val = st.number_input("Min Value", value=1)
                    with col2:
                        max_val = st.number_input("Max Value", value=5)
                
                elif question_type == "multiple_choice":
                    options = st.text_area(
                        "Options (one per line)",
                        placeholder="Enter one option per line...",
                        help="Each line will be a separate option"
                    )

                # Preview section
                if question_text:
                    st.write("---")
                    st.write("Preview:")
                    st.write(question_text)
                    
                    if question_type == "scale":
                        st.slider("", min_value=min_val, max_value=max_val, value=min_val, disabled=True)
                    elif question_type == "multiple_choice":
                        options_list = [opt.strip() for opt in options.split("\n") if opt.strip()]
                        if options_list:
                            st.selectbox("", options_list, disabled=True)
                    elif question_type == "text":
                        st.text_area("", disabled=True)
                    elif question_type == "voice":
                        st.text_area("", disabled=True)
                        st.info("🎤 Voice recording will be available here")

                # Submit button
                if st.form_submit_button("Add Question"):
                    if not question_text:
                        st.error("Please enter a question text")
                        return
                        
                    if question_type == "multiple_choice" and not options.strip():
                        st.error("Please add at least one option for multiple choice question")
                        return
                        
                    try:
                        # Prepare question data
                        question_data = {
                            "text": question_text,
                            "type": question_type,
                            "is_final": is_final,
                            "required": True,
                            "order": len(self.surveys[0]["questions"])
                        }
                        
                        if question_type == "scale":
                            question_data["scale_range"] = (min_val, max_val)
                        elif question_type == "multiple_choice":
                            question_data["options"] = [opt.strip() for opt in options.split("\n") if opt.strip()]
                        
                        # Send to backend
                        response = requests.post(
                            f"{self.API_URL}/api/surveys/{self.surveys[0]['id']}/questions",
                            json=question_data
                        )
                        
                        if response.status_code == 200:
                            st.success("Question added successfully!")
                            st.rerun()
                        else:
                            st.error(f"Error adding question: {response.text}")
                    except Exception as e:
                        st.error(f"Error adding question: {str(e)}")
        
        # Display existing questions
        st.header("Existing Questions")
        for question in sorted(self.surveys[0]["questions"], key=lambda x: x["order"]):
            with st.expander(f"Q{question['order'] + 1}: {question['text']}", expanded=False):
                self._display_question_editor(
                    question,
                    self.surveys[0]["questions"][:question["order"]]
                )
    
    def _update_question(self, survey_id: str, question: dict) -> bool:
        """Update a question in the survey"""
        try:
            # Create updated question data
            updated_question = question.copy()
            if question["id"] in st.session_state.current_conditions:
                updated_question["conditions"] = st.session_state.current_conditions[question["id"]]
                
            # Using POST instead of PUT since the API might not support PUT
            response = requests.post(
                f"{self.API_URL}/api/surveys/{survey_id}/questions/{question['id']}/update",
                json=updated_question
            )
            
            if response.status_code == 200:
                return True
            else:
                st.error(f"Error updating question: {response.text}")
                return False
        except Exception as e:
            st.error(f"Error updating question: {str(e)}")
            return False
                
def main():
    st.set_page_config(
        page_title="Levi's Chatbot",
        page_icon="��",
        layout="wide"
    )

    # Initialize components
    chat_ui = ChatUI()
    survey_admin_ui = SurveyAdminUI()

    # Sidebar navigation
    with st.sidebar:
        st.title("Navigation")
        selected_page = st.radio("", ["Chat", "Survey Admin"])

    # Display selected page
    if selected_page == "Chat":
        chat_ui.display_chat_interface()
    else:
        survey_admin_ui.display_survey_admin()

if __name__ == "__main__":
    main()