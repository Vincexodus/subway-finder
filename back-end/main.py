#!/usr/bin/env python3
"""
FastAPI Backend for Subway Outlet Data
Serves outlet data with geographical coordinates and provides chatbot functionality
"""

from fastapi import FastAPI, HTTPException, Query, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging
from contextlib import asynccontextmanager
import os
from supabase import create_client, Client
import math
from openai import OpenAI
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import requests
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and Key must be set in environment variables.")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Pydantic models
class Outlet(BaseModel):
    id: int
    name: str
    address: str
    operating_hours: Optional[str] = None
    waze_link: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class OutletWithDistance(Outlet):
    distance_km: Optional[float] = None

class OutletChat(BaseModel):
    name: str
    address: str
    operating_hours: Optional[str] = None

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str

# Haversine formula to calculate distance between two lat/lng points
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# Initialize model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def build_vector_store(outlets):
    outlet_texts = [
        f"{o['name']} at {o['address']}. Hours: {o.get('operating_hours', 'N/A')}"
        for o in outlets
    ]
    # Convert embeddings to float32
    embeddings = embedder.encode(outlet_texts, convert_to_numpy=True).astype(np.float32)

    # Build FAISS index
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings) # type: ignore

    return index, outlet_texts


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Subway Outlet API")
    yield
    logger.info("Shutting down Subway Outlet API")

# FastAPI app
app = FastAPI(
    title="Subway Outlet API",
    description="API for Subway outlet data with geocoding and catchment analysis",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/outlets", response_model=List[Outlet])
def get_all_outlets():
    """Get all outlets from Supabase"""
    try:
        response = supabase.table("outlets").select("*").execute()
        outlets = response.data or []
        return outlets
    except Exception as e:
        logger.error(f"Error fetching outlets: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch outlets")

@app.get("/outlets/nearby", response_model=List[OutletWithDistance])
def get_nearby_outlets(
    latitude: float = Query(..., description="Latitude of the location"),
    longitude: float = Query(..., description="Longitude of the location"),
    distance_km: float = Query(5, description="Search radius in kilometers")
):
    """Find nearby outlets within a given distance (default 5km)"""
    try:
        response = supabase.table("outlets").select("*").not_.is_("latitude", None).not_.is_("longitude", None).execute()
        outlets = response.data or []
        results = []
        for outlet in outlets:
            lat = outlet.get("latitude")
            lng = outlet.get("longitude")
            if lat is not None and lng is not None:
                dist = haversine(latitude, longitude, lat, lng)
                if dist <= distance_km:
                    outlet_with_distance = dict(outlet)
                    outlet_with_distance["distance_km"] = round(dist, 3)
                    results.append(outlet_with_distance)
        results.sort(key=lambda x: x["distance_km"])
        return results
    except Exception as e:
        logger.error(f"Error finding nearby outlets: {e}")
        raise HTTPException(status_code=500, detail="Failed to find nearby outlets")

@app.post("/chat-completion", response_model=ChatResponse)
def chat_completion(request: ChatRequest):
    try:
        # Step 1: Fetch data from Supabase
        outlets = get_all_outlets()

        # Step 2: Build vector index
        index, outlet_texts = build_vector_store(outlets)

        # Step 3: Embed user query
        query_embedding = embedder.encode(request.query, convert_to_numpy=True)

        # Step 4: Search for top matches
        # 30,000 token limit for Llama 4 Scout
        k = min(20, len(outlet_texts))
        D, I = index.search(np.array([query_embedding]), k=k) # type: ignore
        top_matches = [outlet_texts[i] for i in I[0]]

        # Step 5: Build prompt
        context = "\n".join(top_matches)
        prompt = f"""
            You are an assistant for outlet information. Use the outlet data below to answer the user's question.

            Outlet Data:
            {context}

            User Question: {request.query}
            Answer:
        """

        # Step 6: Call Groq API
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}"
        }
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 256,
        }
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        answer = content.strip() if content is not None else "No answer generated."
        return ChatResponse(answer=answer)

    except Exception as e:
        logger.error(f"Groq API error: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {e}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)