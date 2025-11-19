import os
from datetime import date, datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import db, create_document, get_documents
from bson import ObjectId

app = FastAPI(title="FitCheck API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Utilities --------------------

def to_str_id(doc):
    if not doc:
        return doc
    d = {**doc}
    if d.get("_id"):
        d["id"] = str(d.pop("_id"))
    # cast dates to isoformat
    for k, v in list(d.items()):
        if isinstance(v, (datetime, date)):
            d[k] = v.isoformat()
    return d


def oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")


# -------------------- Schemas --------------------

class ItemCreate(BaseModel):
    image_url: str
    category: str
    season: str = "All"
    color: Optional[str] = None
    brand: Optional[str] = None
    last_worn_date: Optional[date] = None


class OutfitCreate(BaseModel):
    items: List[str] = Field(..., description="List of item IDs")
    is_favorite: bool = False


class FavoriteToggle(BaseModel):
    is_favorite: bool


# -------------------- Basic routes --------------------

@app.get("/")
def read_root():
    return {"message": "FitCheck Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, 'name', None) or "Unknown"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# -------------------- Items --------------------

@app.get("/api/items")
def list_items(category: Optional[str] = None):
    filt = {"category": category} if category else {}
    items = get_documents("item", filt)
    return [to_str_id(i) for i in items]


@app.post("/api/items")
def create_item(payload: ItemCreate):
    item_id = create_document("item", payload.model_dump())
    # return the created doc
    doc = db["item"].find_one({"_id": ObjectId(item_id)})
    return to_str_id(doc)


# -------------------- Outfits --------------------

@app.get("/api/outfits")
def list_outfits(favorite: Optional[bool] = None):
    filt = {}
    if favorite is not None:
        filt["is_favorite"] = favorite
    outfits = list(db["outfit"].find(filt).sort("created_at", -1))
    return [to_str_id(o) for o in outfits]


@app.post("/api/outfits")
def create_outfit(payload: OutfitCreate):
    # validate item ids exist
    ids = [oid(i) for i in payload.items]
    count = db["item"].count_documents({"_id": {"$in": ids}})
    if count != len(ids):
        raise HTTPException(status_code=400, detail="One or more items not found")
    outfit_id = create_document(
        "outfit",
        {
            "items": [str(i) for i in payload.items],
            "date_created": datetime.utcnow(),
            "is_favorite": payload.is_favorite,
        },
    )
    doc = db["outfit"].find_one({"_id": ObjectId(outfit_id)})
    return to_str_id(doc)


@app.patch("/api/outfits/{outfit_id}/favorite")
def toggle_favorite(outfit_id: str, payload: FavoriteToggle):
    res = db["outfit"].update_one({"_id": oid(outfit_id)}, {"$set": {"is_favorite": payload.is_favorite, "updated_at": datetime.utcnow()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Outfit not found")
    doc = db["outfit"].find_one({"_id": oid(outfit_id)})
    return to_str_id(doc)


# -------------------- Shuffle --------------------

@app.get("/api/shuffle")
def shuffle_outfit():
    """Randomly pick one Top, one Bottom, and one Shoes."""
    required = ["Top", "Bottom", "Shoes"]
    selected: List[dict] = []
    for cat in required:
        pipeline = [{"$match": {"category": cat}}, {"$sample": {"size": 1}}]
        docs = list(db["item"].aggregate(pipeline))
        if docs:
            selected.append(to_str_id(docs[0]))
    if len(selected) != 3:
        # Not enough items to build full outfit
        return {"items": selected, "complete": False}
    return {"items": selected, "complete": True}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
