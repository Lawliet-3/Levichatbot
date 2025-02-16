from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions
import pandas as pd
from ..models.product import Product
import logging

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, persist_directory: str = "data/chroma_db"):
        """Initialize the RAG service with ChromaDB."""
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = None
        
    def initialize_collection(self, name: str = "levis_products", reset: bool = False) -> None:
        """Initialize or get the ChromaDB collection."""
        try:
            # If reset is True, try to delete existing collection
            if reset:
                try:
                    self.client.delete_collection(name)
                    logger.info(f"Deleted existing collection: {name}")
                except ValueError:
                    # Collection didn't exist, that's fine
                    pass

            # Always create a new collection
            self.collection = self.client.create_collection(
                name=name,
                embedding_function=self.embedding_function,
                metadata={"description": "Levis product database"}
            )
            logger.info(f"Created new collection: {name}")
                
        except ValueError as e:
            # Collection already exists, just get it
            logger.info(f"Collection {name} already exists, retrieving it...")
            self.collection = self.client.get_collection(
                name=name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Retrieved existing collection: {name}")
        except Exception as e:
            logger.error(f"Error initializing collection: {e}")
            raise
    
    def load_products(self, csv_path: str) -> List[Product]:
        """Load products from CSV file with proper data cleaning."""
        try:
            # Read CSV with pandas
            df = pd.read_csv(csv_path)
            
            # Convert NaN to None for proper JSON serialization
            df = df.replace({pd.NA: None})
            
            products = []
            for _, row in df.iterrows():
                try:
                    # Use the new from_dict method
                    product = Product.from_dict(row.to_dict())
                    products.append(product)
                except Exception as e:
                    logger.error(f"Error loading product: {e}")
                    logger.debug(f"Problematic row data: {row.to_dict()}")
                    continue
                    
            logger.info(f"Successfully loaded {len(products)} products")
            return products
            
        except Exception as e:
            logger.error(f"Error loading products from CSV: {e}")
            raise

    def index_products(self, products: List[Product]) -> None:
        """Index products in the vector database."""
        if not self.collection:
            raise ValueError("Collection not initialized. Call initialize_collection first.")

        try:
            # Prepare data for ChromaDB
            ids = [f"product_{i}" for i in range(len(products))]
            texts = [product.to_embedding_text() for product in products]
            metadatas = [product.model_dump(exclude_none=True) for product in products]  # Exclude None values

            # Add documents in batches
            batch_size = 100
            total_products = len(products)
            
            for i in range(0, total_products, batch_size):
                end_idx = min(i + batch_size, total_products)
                try:
                    self.collection.add(
                        ids=ids[i:end_idx],
                        documents=texts[i:end_idx],
                        metadatas=metadatas[i:end_idx]
                    )
                    logger.info(f"Indexed products {i} to {end_idx}")
                except Exception as e:
                    logger.error(f"Error indexing batch {i} to {end_idx}: {e}")
                    raise
                    
            logger.info(f"Successfully indexed all {total_products} products")
        except Exception as e:
            logger.error(f"Error indexing products: {e}")
            raise

    def query_products(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Query the vector database for relevant products."""
        if not self.collection:
            raise ValueError("Collection not initialized. Call initialize_collection first.")

        try:
            # Extract product numbers from query
            import re
            product_numbers = re.findall(r'\d{3}', query)
            
            # First try direct product number search
            if product_numbers:
                # For each product number, create multiple search patterns
                search_patterns = []
                for num in product_numbers:
                    search_patterns.extend([
                        f"Levi's {num}",
                        f"{num}",
                        f"Levi's® {num}",
                        f"Levi's {num}™"
                    ])
                
                # Try each pattern
                for pattern in search_patterns:
                    results = self.collection.query(
                        query_texts=[pattern],
                        n_results=n_results,
                        include=["documents", "metadatas"]
                    )
                    
                    # Check if we got any results
                    if results["documents"][0]:
                        formatted_results = []
                        for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                            # Verify the product number is in the name
                            if any(num in metadata["product_name"] for num in product_numbers):
                                formatted_results.append({
                                    "content": doc,
                                    "metadata": metadata
                                })
                        
                        if formatted_results:
                            return formatted_results
            
            # If no results found with product numbers or no numbers in query,
            # try a general search
            keywords = query.lower().split()
            search_terms = [
                query,  # Original query
                " ".join([w for w in keywords if w not in ["show", "me", "the", "a", "an"]]),  # Without stop words
                " ".join([w for w in keywords if len(w) > 2])  # Without very short words
            ]
            
            for term in search_terms:
                results = self.collection.query(
                    query_texts=[term],
                    n_results=n_results,
                    include=["documents", "metadatas"]
                )
                
                if results["documents"][0]:
                    formatted_results = []
                    for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                        formatted_results.append({
                            "content": doc,
                            "metadata": metadata
                        })
                    
                    if formatted_results:
                        return formatted_results
            
            # If still no results, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Error querying products: {e}")
            return []