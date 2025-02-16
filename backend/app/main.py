from fastapi import FastAPI, HTTPException
from typing import Dict, Any
import logging
from pathlib import Path
from dotenv import load_dotenv
import os
import pandas as pd

from app.services.survey_service import SurveyService
from app.models.survey import Survey, Question, Answer

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from app.services.rag_service import RAGService
from app.services.chat_service import ChatService
from app.models.product import ProductQuery

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Levi's Chatbot API")

# Initialize survey service
survey_service = SurveyService()

# Add these endpoints to your FastAPI app

@app.post("/api/surveys")
async def create_survey(survey_data: dict):
    return await survey_service.create_survey(survey_data)

@app.get("/api/surveys")
async def list_surveys():
    return await survey_service.get_surveys()

@app.get("/api/surveys/{survey_id}")
async def get_survey(survey_id: str):
    return await survey_service.get_survey(survey_id)

@app.put("/api/surveys/{survey_id}")
async def update_survey(survey_id: str, updates: dict):
    return await survey_service.update_survey(survey_id, updates)

@app.delete("/api/surveys/{survey_id}")
async def delete_survey(survey_id: str):
    return await survey_service.delete_survey(survey_id)

@app.post("/api/survey/start")
async def start_survey(data: dict):
    return await survey_service.start_survey(data["survey_id"], data["user_id"])

@app.post("/api/survey/answer")
async def submit_answer(data: dict):
    return await survey_service.submit_answer(
        data["survey_id"],
        data["user_id"],
        data["answer"]
    )

@app.get("/api/surveys/{survey_id}/results")
async def get_survey_results(survey_id: str):
    return await survey_service.get_survey_results(survey_id)
# Initialize services
rag_service = RAGService(persist_directory="data/chroma_db")
chat_service = ChatService(rag_service)

# Verify the API key is loaded
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

@app.on_event("startup")
async def startup_event():
    """Initialize the RAG service and load products on startup."""
    try:
        # Verify environment variables
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OPENAI_API_KEY not found in environment variables")
            raise ValueError("OPENAI_API_KEY not configured")
        else:
            logger.info("OPENAI_API_KEY is configured")

        # Initialize the collection with new improvements
        logger.info("Initializing RAG collection...")
        rag_service.initialize_collection(reset=True)  # This will use improved embedding
        
        # Load and index products
        csv_path = Path("data/products.csv")
        if csv_path.exists():
            logger.info(f"Loading products from {csv_path}...")
            # This will use improved product loading with better text representation
            products = rag_service.load_products(str(csv_path))
            logger.info(f"Loaded {len(products)} products")
            
            # Only index if there are products to index
            if products:
                logger.info("Indexing products with improved search capabilities...")
                rag_service.index_products(products)  # This will use improved indexing
                logger.info(f"Successfully indexed {len(products)} products")
                
                # Verify indexing with a test query
                test_results = rag_service.query_products("578 baggy jeans")
                if test_results:
                    logger.info("Product indexing verification successful")
                else:
                    logger.warning("Product indexing verification returned no results")
            else:
                logger.warning("No products loaded from CSV")
        else:
            logger.error(f"Products CSV file not found at {csv_path}")
            raise FileNotFoundError(f"Products CSV file not found at {csv_path}")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        # Log the error but don't raise it to allow the server to start
        pass
@app.get("/health")
async def health_check():
    """Health check endpoint to verify service status."""
    try:
        # Verify that the collection is initialized
        if not rag_service.collection:
            rag_service.initialize_collection()
        return {"status": "healthy", "message": "Service is running and collection is initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/query")
async def query_products(query: ProductQuery) -> Dict[str, Any]:
    """Handle product queries through the chat interface."""
    try:
        result = chat_service.handle_product_query(query.query)
        return result
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/products/{product_id}")
async def get_product(product_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific product."""
    try:
        result = chat_service.get_product_details(product_id)
        if not result["product"]:
            raise HTTPException(status_code=404, detail="Product not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving product: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/collection")
async def debug_collection():
    """Debug endpoint to check collection status."""
    try:
        # Check if collection exists
        if not rag_service.collection:
            return {"status": "error", "message": "Collection not initialized"}
            
        # Test query to verify data
        test_results = rag_service.query_products("test")
        
        return {
            "status": "ok",
            "collection_name": rag_service.collection.name,
            "number_of_results": len(test_results),
            "sample_results": test_results[:1] if test_results else []
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/debug/validate-data")
async def validate_data():
    """Validate the CSV data and return statistics."""
    try:
        csv_path = Path("data/products.csv")
        if not csv_path.exists():
            return {"status": "error", "message": "products.csv not found"}
            
        df = pd.read_csv(csv_path)
        
        # Get basic statistics
        stats = {
            "total_rows": len(df),
            "columns": list(df.columns),
            "null_counts": df.isnull().sum().to_dict(),
            "sample_rows": df.head(3).to_dict('records')
        }
        
        return {
            "status": "ok",
            "statistics": stats
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/surveys/{survey_id}/questions")
async def add_question(survey_id: str, question_data: Dict[str, Any]):
    """Add a question to an existing survey"""
    try:
        survey = await survey_service.get_survey(survey_id)
        if not survey:
            raise HTTPException(status_code=404, detail="Survey not found")
        
        # Create question object and add it to the survey
        new_question = {
            "text": question_data["text"],
            "type": question_data["type"],
            "order": len(survey.questions),
            "required": True
        }
        
        # Add type-specific fields
        if question_data["type"] == "multiple_choice":
            new_question["options"] = question_data.get("options", [])
        elif question_data["type"] == "scale":
            new_question["scale_range"] = (
                question_data.get("min_val", 1),
                question_data.get("max_val", 5)
            )
        
        # Update the survey with the new question
        return await survey_service.add_question(survey_id, new_question)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/surveys/{survey_id}/questions/{question_id}")
async def delete_question(survey_id: str, question_id: str):
    """Delete a question from a survey"""
    try:
        return await survey_service.delete_question(survey_id, question_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.post("/api/surveys/{survey_id}/questions/{question_id}/update")
async def update_survey_question(
    survey_id: str, 
    question_id: str, 
    question_data: Dict[str, Any]
):
    """Update a specific question in a survey"""
    try:
        updated_survey = await survey_service.update_question(survey_id, question_id, question_data)
        return {"message": "Question updated successfully", "survey": updated_survey}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/surveys/{survey_id}")
async def update_survey(survey_id: str, updates: Dict[str, Any]):
    """Update a survey"""
    try:
        updated_survey = await survey_service.update_survey(survey_id, updates)
        return updated_survey
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))