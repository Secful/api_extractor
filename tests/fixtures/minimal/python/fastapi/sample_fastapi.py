"""Sample FastAPI application for testing."""

from fastapi import FastAPI, APIRouter, Header, Query, Depends
from pydantic import BaseModel
from typing import Optional, List


app = FastAPI()
router = APIRouter(prefix="/api")


class Item(BaseModel):
    """Item model."""

    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None


class User(BaseModel):
    """User model."""

    id: int
    username: str
    email: str


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Hello World"}


@app.get("/users/{user_id}")
async def get_user(user_id: int, token: str = Header(...)):
    """Get user by ID."""
    return {"id": user_id, "token": token}


@app.post("/users")
async def create_user(user: User):
    """Create a new user."""
    return user


@app.get("/items")
async def list_items(
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(10, description="Maximum number of items"),
):
    """List items with pagination."""
    return {"skip": skip, "limit": limit}


@router.get("/products/{product_id}")
async def get_product(product_id: str, include_details: bool = Query(False)):
    """Get product by ID."""
    return {"id": product_id, "include_details": include_details}


@router.post("/products")
async def create_product(item: Item):
    """Create a new product."""
    return item


@router.put("/products/{product_id}")
async def update_product(product_id: str, item: Item):
    """Update a product."""
    return {"id": product_id, **item.dict()}


@router.delete("/products/{product_id}")
async def delete_product(product_id: str):
    """Delete a product."""
    return {"deleted": product_id}


app.include_router(router)
