from typing import List, Optional, Dict, Any, Union, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import uuid

class QuestionType(str, Enum):
    SCALE = "scale"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    VOICE = "voice"

class ConditionalOperator(str, Enum):
    EQUALS = "equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"

class Condition(BaseModel):
    previous_question_id: str
    operator: ConditionalOperator
    value: Any

    def evaluate(self, previous_answer: Any) -> bool:
        """Evaluate if the condition is met"""
        if previous_answer is None:
            return False

        if self.operator == ConditionalOperator.EQUALS:
            return previous_answer == self.value
        elif self.operator == ConditionalOperator.GREATER_THAN:
            return float(previous_answer) > float(self.value)
        elif self.operator == ConditionalOperator.LESS_THAN:
            return float(previous_answer) < float(self.value)
        return False

class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order: int
    text: str
    type: QuestionType
    is_final: bool = False  # True for the final open-ended question
    required: bool = True
    options: Optional[List[str]] = None  # For multiple choice
    scale_range: Optional[Tuple[int, int]] = None  # For scale questions
    conditions: Optional[List[Condition]] = None
    follow_up_question_id: Optional[str] = None  # ID of a follow-up question
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def should_show(self, previous_answers: Dict[str, Any]) -> bool:
        """Determine if this question should be shown based on previous answers"""
        if not self.conditions:
            return True

        return all(
            condition.evaluate(previous_answers.get(condition.previous_question_id))
            for condition in self.conditions
        )

class Answer(BaseModel):
    question_id: str
    value: Any
    timestamp: datetime = Field(default_factory=datetime.now)

class SurveyState(BaseModel):
    """Tracks the state of a survey session"""
    current_question_idx: int = 0
    answered_questions: List[str] = Field(default_factory=list)
    skipped_questions: List[str] = Field(default_factory=list)
    answers: Dict[str, Any] = Field(default_factory=dict)
    is_structured_complete: bool = False  # True when all non-final questions are done
    is_complete: bool = False
    last_interaction: datetime = Field(default_factory=datetime.now)

    def add_answer(self, question_id: str, answer: Any):
        """Record an answer and update state"""
        self.answered_questions.append(question_id)
        self.answers[question_id] = answer
        self.last_interaction = datetime.now()

    def skip_question(self, question_id: str):
        """Record a skipped question"""
        self.skipped_questions.append(question_id)

class Survey(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    questions: List[Question]
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def get_next_question(self, state: SurveyState) -> Optional[Question]:
        """Get the next applicable question based on state and conditions"""
        if state.is_complete:
            return None

        # If structured questions are complete, return final question if not answered
        if state.is_structured_complete:
            final_question = next((q for q in self.questions if q.is_final), None)
            if final_question and final_question.id not in state.answered_questions:
                return final_question
            return None

        # Get non-final questions that haven't been answered or skipped
        pending_questions = [
            q for q in self.questions
            if not q.is_final
            and q.id not in state.answered_questions
            and q.id not in state.skipped_questions
        ]

        # Sort by order
        pending_questions.sort(key=lambda x: x.order)

        # Find the next applicable question
        for question in pending_questions:
            if question.should_show(state.answers):
                return question

        # If no more structured questions, mark structured portion complete
        state.is_structured_complete = True
        return self.get_next_question(state)  # Recursively check for final question

    def validate_answer(self, question: Question, answer: Any) -> bool:
        """Validate if an answer is acceptable for a given question"""
        if question.required and (answer is None or answer == ""):
            return False

        if question.type == QuestionType.SCALE:
            try:
                value = float(answer)
                return question.scale_range[0] <= value <= question.scale_range[1]
            except (ValueError, TypeError):
                return False

        elif question.type == QuestionType.MULTIPLE_CHOICE:
            return answer in question.options

        return True

    class Config:
        arbitrary_types_allowed = True

class SurveyResponse(BaseModel):
    survey_id: str
    user_id: str
    conversation_id: str
    answers: List[Answer]
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def complete(self):
        """Mark the survey response as completed"""
        self.completed = True
        self.completed_at = datetime.now()

class SurveyService:
    def __init__(self):
        """Initialize survey service with storage for surveys and states"""
        self.surveys: Dict[str, Survey] = {}
        self.survey_states: Dict[str, Dict[str, SurveyState]] = {}
        self.responses: Dict[str, Dict[str, SurveyResponse]] = {}
        
    def create_survey(self, survey: Survey) -> Survey:
        """Create a new survey"""
        survey.created_at = datetime.now()
        survey.updated_at = datetime.now()
        self.surveys[survey.id] = survey
        return survey
        
    def update_survey(self, survey_id: str, updates: Dict[str, Any]) -> Optional[Survey]:
        """Update an existing survey"""
        if survey_id not in self.surveys:
            return None
            
        survey = self.surveys[survey_id]
        for key, value in updates.items():
            if hasattr(survey, key):
                setattr(survey, key, value)
        
        survey.updated_at = datetime.now()
        return survey
        
    def delete_survey(self, survey_id: str) -> bool:
        """Delete a survey"""
        if survey_id in self.surveys:
            del self.surveys[survey_id]
            return True
        return False
        
    def start_survey(self, survey_id: str, user_id: str, conversation_id: str) -> Dict[str, Any]:
        """Start a new survey session for a user"""
        survey = self.surveys.get(survey_id)
        if not survey:
            raise ValueError(f"Survey {survey_id} not found")
            
        # Initialize or reset survey state
        if survey_id not in self.survey_states:
            self.survey_states[survey_id] = {}
        self.survey_states[survey_id][user_id] = SurveyState()
        
        # Initialize survey response
        if survey_id not in self.responses:
            self.responses[survey_id] = {}
        self.responses[survey_id][user_id] = SurveyResponse(
            survey_id=survey_id,
            user_id=user_id,
            conversation_id=conversation_id,
            answers=[]
        )
        
        # Get first question
        first_question = survey.get_next_question(self.survey_states[survey_id][user_id])
        
        return {
            "survey": survey,
            "current_question": first_question
        }
        
    def submit_answer(
        self, 
        survey_id: str, 
        user_id: str, 
        answer: Answer
    ) -> Dict[str, Any]:
        """Submit an answer and get the next question"""
        survey = self.surveys.get(survey_id)
        if not survey:
            raise ValueError(f"Survey {survey_id} not found")
            
        state = self.survey_states[survey_id][user_id]
        response = self.responses[survey_id][user_id]
        
        # Validate answer
        current_question = survey.questions[state.current_question_idx]
        if not survey.validate_answer(current_question, answer.value):
            raise ValueError("Invalid answer provided")
        
        # Add answer
        response.answers.append(answer)
        state.mark_question_completed(answer.question_id, answer.value)
        
        # Move to next question
        state.current_question_idx += 1
        
        # Get next question
        next_question = survey.get_next_question(state)
        
        # Check if survey is completed
        if not next_question:
            state.is_complete = True
            response.complete()
            
        return {
            "next_question": next_question,
            "completed": state.is_complete
        }
        
    def get_survey_analytics(self, survey_id: str) -> Dict[str, Any]:
        """Get analytics for a survey"""
        if survey_id not in self.responses:
            return {}
            
        responses = self.responses[survey_id].values()
        total_responses = len(responses)
        completed_responses = len([r for r in responses if r.completed])
        
        # Calculate average completion time
        completion_times = [
            (r.completed_at - r.created_at).total_seconds()
            for r in responses
            if r.completed and r.completed_at
        ]
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        
        # Analyze answers per question
        answer_distribution = {}
        for response in responses:
            for answer in response.answers:
                if answer.question_id not in answer_distribution:
                    answer_distribution[answer.question_id] = []
                answer_distribution[answer.question_id].append(answer.value)
        
        return {
            "total_responses": total_responses,
            "completed_responses": completed_responses,
            "completion_rate": (completed_responses / total_responses * 100) if total_responses > 0 else 0,
            "average_completion_time_seconds": avg_completion_time,
            "answer_distribution": answer_distribution
        }