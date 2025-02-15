from fastapi import HTTPException
from typing import Dict, List, Optional, Any
from datetime import datetime
from ..models.survey import (
    Survey, Question, SurveyState, Answer,
    QuestionType, ConditionalOperator, Condition
)
import logging

logger = logging.getLogger(__name__)

class SurveyService:
    def __init__(self):
        self.surveys: Dict[str, Survey] = {}
        self.survey_states: Dict[str, Dict[str, SurveyState]] = {}
        self._create_default_survey()

    def _create_default_survey(self):
        """Create the default survey with proper conditional logic"""
        default_survey = Survey(
            title="Product Experience Survey",
            description="Help us improve our products by sharing your experience",
            questions=[
                # Product Quality Satisfaction
                Question(
                    id="q1",
                    order=0,
                    text="On a scale from 1 to 5, how satisfied are you with the overall quality of the product you viewed or purchased?",
                    type=QuestionType.SCALE,
                    scale_range=(1, 5),
                    required=True
                ),
                
                # Design & Fit Evaluation
                Question(
                    id="q2",
                    order=1,
                    text="How would you rate the design and fit of the product?",
                    type=QuestionType.MULTIPLE_CHOICE,
                    options=["Excellent", "Good", "Average", "Poor"],
                    required=True,
                    conditions=[
                        Condition(
                            previous_question_id="q1",
                            operator=ConditionalOperator.GREATER_THAN,
                            value=2  # Only show if quality rating > 2
                        )
                    ]
                ),
                
                # Design Improvement (shown if design is Poor)
                Question(
                    id="q3",
                    order=2,
                    text="Which aspects of design or fit could be improved?",
                    type=QuestionType.TEXT,
                    required=True,
                    conditions=[
                        Condition(
                            previous_question_id="q2",
                            operator=ConditionalOperator.EQUALS,
                            value="Poor"
                        )
                    ]
                ),
                
                # Usage Experience
                Question(
                    id="q4",
                    order=3,
                    text="Which of the following best describes your experience with the product?",
                    type=QuestionType.MULTIPLE_CHOICE,
                    options=["Exceeded expectations", "Met expectations", "Below expectations"],
                    required=True,
                    conditions=[
                        Condition(
                            previous_question_id="q1",
                            operator=ConditionalOperator.GREATER_THAN,
                            value=2  # Only show if quality rating > 2
                        )
                    ]
                ),
                
                # Improvement Suggestions (shown if experience is Below expectations)
                Question(
                    id="q5",
                    order=4,
                    text="What improvements would you suggest to better meet your expectations?",
                    type=QuestionType.TEXT,
                    required=True,
                    conditions=[
                        Condition(
                            previous_question_id="q4",
                            operator=ConditionalOperator.EQUALS,
                            value="Below expectations"
                        )
                    ]
                ),
                
                # Purchase Decision Factors
                Question(
                    id="q6",
                    order=5,
                    text="What was the most important factor in your purchase decision?",
                    type=QuestionType.MULTIPLE_CHOICE,
                    options=["Price", "Brand Reputation", "Product Features", "Design", "Other"],
                    required=True
                ),
                
                # Other Factor Clarification
                Question(
                    id="q7",
                    order=6,
                    text="Please specify what other factor influenced your purchase decision:",
                    type=QuestionType.TEXT,
                    required=True,
                    conditions=[
                        Condition(
                            previous_question_id="q6",
                            operator=ConditionalOperator.EQUALS,
                            value="Other"
                        )
                    ]
                ),
                
                # Final Feedback
                Question(
                    id="q8",
                    order=7,
                    text="Please provide any additional comments or suggestions that could help us improve our products or services.",
                    type=QuestionType.TEXT,
                    is_final=True,
                    required=True
                )
            ]
        )
        self.surveys[default_survey.id] = default_survey

    async def create_survey(self, survey_data: Dict[str, Any]) -> Survey:
        """Create a new survey"""
        try:
            survey = Survey(**survey_data)
            self.surveys[survey.id] = survey
            return survey
        except Exception as e:
            logger.error(f"Error creating survey: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def get_surveys(self) -> List[Survey]:
        """Get all surveys"""
        return list(self.surveys.values())

    async def get_survey(self, survey_id: str) -> Optional[Survey]:
        """Get a survey by ID"""
        survey = self.surveys.get(survey_id)
        if not survey:
            raise HTTPException(status_code=404, detail="Survey not found")
        return survey

    async def add_question(self, survey_id: str, question_data: Dict[str, Any]) -> Survey:
        """Add a question to a survey"""
        survey = self.surveys.get(survey_id)
        if not survey:
            raise HTTPException(status_code=404, detail="Survey not found")

        # Set order to be last if not specified
        if 'order' not in question_data:
            question_data['order'] = len(survey.questions)

        question = Question(**question_data)
        survey.questions.append(question)
        survey.updated_at = datetime.now()
        return survey

    async def reorder_questions(self, survey_id: str, question_orders: List[Dict[str, int]]) -> Survey:
        """Update the order of questions"""
        survey = self.surveys.get(survey_id)
        if not survey:
            raise HTTPException(status_code=404, detail="Survey not found")

        # Update orders
        for order_update in question_orders:
            question = next(
                (q for q in survey.questions if q.id == order_update["question_id"]),
                None
            )
            if question:
                question.order = order_update["order"]

        # Sort questions by order
        survey.questions.sort(key=lambda x: x.order)
        survey.updated_at = datetime.now()
        return survey

    async def start_survey(self, survey_id: str, user_id: str) -> Dict[str, Any]:
        """Start a new survey session"""
        survey = self.surveys.get(survey_id)
        if not survey:
            raise HTTPException(status_code=404, detail="Survey not found")

        # Initialize or reset state
        if survey_id not in self.survey_states:
            self.survey_states[survey_id] = {}

        state = SurveyState()
        self.survey_states[survey_id][user_id] = state

        # Get first question
        next_question = survey.get_next_question(state)
        if not next_question:
            raise HTTPException(status_code=400, detail="No questions available")

        return {
            "current_question": next_question.dict(),
            "progress": {
                "answered": len(state.answered_questions),
                "total": len([q for q in survey.questions if not q.is_final]),
                "is_final": next_question.is_final
            }
        }

    async def submit_answer(
        self,
        survey_id: str,
        user_id: str,
        answer: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit an answer and get the next question"""
        survey = self.surveys.get(survey_id)
        if not survey:
            raise HTTPException(status_code=404, detail="Survey not found")

        state = self.survey_states.get(survey_id, {}).get(user_id)
        if not state:
            raise HTTPException(status_code=400, detail="Survey session not found")

        # Validate answer
        question = next(
            (q for q in survey.questions if q.id == answer["question_id"]),
            None
        )
        if not question:
            raise HTTPException(status_code=400, detail="Question not found")

        if not survey.validate_answer(question, answer["value"]):
            raise HTTPException(status_code=400, detail="Invalid answer")

        # Record answer
        state.add_answer(answer["question_id"], answer["value"])

        # Get next question
        next_question = survey.get_next_question(state)

        # Check if survey is complete
        if not next_question:
            state.is_complete = True
            return {
                "completed": True,
                "message": "Survey completed"
            }

        return {
            "completed": False,
            "next_question": next_question.dict(),
            "progress": {
                "answered": len(state.answered_questions),
                "total": len([q for q in survey.questions if not q.is_final]),
                "is_final": next_question.is_final
            }
        }

    async def get_survey_results(self, survey_id: str) -> Dict[str, Any]:
        """Get survey results and analytics"""
        survey = await self.get_survey(survey_id)
        responses = self.responses.get(survey_id, {}).values()
        
        if not responses:
            return {"message": "No responses found"}
            
        # Calculate analytics
        total_responses = len(responses)
        completed_responses = len([r for r in responses if r.completed])
        
        # Analyze answers
        answer_analysis = {}
        for question in survey.questions:
            answers = []
            for response in responses:
                answer = next(
                    (a for a in response.answers if a.question_id == question.id),
                    None
                )
                if answer:
                    answers.append(answer.value)
            
            if question.type in [QuestionType.SCALE, QuestionType.MULTIPLE_CHOICE]:
                # Calculate distribution for scale and multiple choice questions
                from collections import Counter
                distribution = Counter(answers)
                answer_analysis[question.id] = {
                    "question_text": question.text,
                    "type": question.type,
                    "distribution": distribution
                }
            else:
                # For text and voice questions, just store the responses
                answer_analysis[question.id] = {
                    "question_text": question.text,
                    "type": question.type,
                    "responses": answers
                }
        
        return {
            "total_responses": total_responses,
            "completed_responses": completed_responses,
            "completion_rate": (completed_responses / total_responses * 100) if total_responses > 0 else 0,
            "question_analysis": answer_analysis
        }

    async def add_question(self, survey_id: str, question_data: Dict[str, Any]) -> Survey:
        """Add a question to a survey"""
        survey = self.surveys.get(survey_id)
        if not survey:
            raise HTTPException(status_code=404, detail="Survey not found")
        
        # Create new question
        question = Question(**question_data)
        
        # Add question to survey
        survey.questions.append(question)
        survey.updated_at = datetime.now()
        
        return survey

    async def delete_question(self, survey_id: str, question_id: str) -> Survey:
        """Delete a question from a survey"""
        survey = self.surveys.get(survey_id)
        if not survey:
            raise HTTPException(status_code=404, detail="Survey not found")
        
        # Find and remove the question
        survey.questions = [q for q in survey.questions if q.id != question_id]
        survey.updated_at = datetime.now()
        
        return survey
    
    async def update_survey(self, survey_id: str, updates: Dict[str, Any]) -> Optional[Survey]:
        """Update an existing survey"""
        if survey_id not in self.surveys:
            raise HTTPException(status_code=404, detail="Survey not found")
            
        survey = self.surveys[survey_id]
        for key, value in updates.items():
            if hasattr(survey, key):
                setattr(survey, key, value)
        
        survey.updated_at = datetime.now()
        return survey

    async def update_question(self, survey_id: str, question_id: str, question_data: Dict[str, Any]) -> Optional[Survey]:
        """Update a specific question in a survey"""
        survey = self.surveys.get(survey_id)
        if not survey:
            raise HTTPException(status_code=404, detail="Survey not found")
        
        # Find and update the question
        for question in survey.questions:
            if question.id == question_id:
                # Update existing question fields
                for key, value in question_data.items():
                    if key != "id":  # Don't update the ID
                        setattr(question, key, value)
                survey.updated_at = datetime.now()
                return survey
                
        raise HTTPException(status_code=404, detail="Question not found")