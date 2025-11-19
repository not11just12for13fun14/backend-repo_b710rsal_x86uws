"""
Database Schemas for FitCheck

Each Pydantic model represents a MongoDB collection.
Collection name = lowercase of class name.

- User -> "user"
- Item -> "item"
- Outfit -> "outfit"
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import date

# Users: Name, Email, Profile Picture.
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    profile_picture: Optional[HttpUrl] = Field(None, description="Profile image URL")

# Items: Image URL, Category (Top, Bottom, Shoes, Outerwear, Accessory),
# Season (Summer, Winter, All), Color, Brand, Last_Worn_Date.
class Item(BaseModel):
    image_url: HttpUrl = Field(..., description="Public image URL of the clothing item")
    category: str = Field(..., description="One of: Top, Bottom, Shoes, Outerwear, Accessory")
    season: str = Field("All", description="One of: Summer, Winter, All")
    color: Optional[str] = Field(None, description="Primary color")
    brand: Optional[str] = Field(None, description="Brand name")
    last_worn_date: Optional[date] = Field(None, description="When it was last worn")

# Outfits: List of Items (Linked), Date_Created, Is_Favorite (Boolean).
class Outfit(BaseModel):
    items: List[str] = Field(..., description="List of linked item IDs as strings")
    date_created: Optional[date] = Field(None, description="Creation date; defaults to today if not provided")
    is_favorite: bool = Field(False, description="Whether the outfit is favorited")
