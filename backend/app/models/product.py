from typing import List, Optional
from pydantic import BaseModel, Field
import pandas as pd

class ProductQuery(BaseModel):
    query: str

class Product(BaseModel):
    product_name: str
    description: str = ""
    how_it_fits: str = ""
    composition_care: str = ""
    sale_price: str = ""
    color: Optional[str] = None
    images: str = ""

    def to_embedding_text(self) -> str:
        """Convert product data to a single text for embedding."""
        # Extract product number if present
        import re
        product_numbers = re.findall(r'\d{3}', self.product_name)
        product_number_text = ""
        if product_numbers:
            product_number_text = f"""
            Product Number: {product_numbers[0]}
            Also known as: Levi's {product_numbers[0]}, {product_numbers[0]} jeans
            """

        color_text = self.color if self.color else "Not specified"
        return f"""
        Product: {self.product_name}
        {product_number_text}
        Description: {self.description}
        How it fits: {self.how_it_fits}
        Composition and care: {self.composition_care}
        Price: {self.sale_price}
        Color: {color_text}
        Keywords: Levi's, Levis, denim, jeans
        """.strip()

    @classmethod
    def from_dict(cls, data: dict) -> "Product":
        """Create a Product instance from a dictionary with data cleaning."""
        # Clean the color field
        if "color" in data:
            if pd.isna(data["color"]) or data["color"] == "nan":
                data["color"] = None
            else:
                data["color"] = str(data["color"])

        # Clean other string fields
        for field in ["product_name", "description", "how_it_fits", "composition_care", "sale_price", "images"]:
            if field in data and pd.isna(data[field]):
                data[field] = ""
            elif field in data:
                data[field] = str(data[field])

        return cls(**data)