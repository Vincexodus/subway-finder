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
import requests
from dotenv import load_dotenv
import uvicorn
import numpy as np
import faiss

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
HUGGINGFACE_TOKEN = os.getenv("HF_TOKEN")
EMBED_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"

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

def get_hf_embedding(texts: list[str]):
    headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}
    resp = requests.post(EMBED_URL, headers=headers, json={"inputs": texts})
    resp.raise_for_status()
    data = resp.json()
    return data  # List of embeddings

def build_vector_store(outlets):
    outlet_texts = [
        f"{o['name']} at {o['address']}. Hours: {o.get('operating_hours', 'N/A')}"
        for o in outlets
    ]
    # Get embeddings from Hugging Face API
    embeddings = get_hf_embedding(outlet_texts)
    embeddings = np.array(embeddings, dtype=np.float32)

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

origins = [
    "https://subway-finder.vercel.app",
    "http://localhost:3000"
]
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # <-- frontend domains you trust
    allow_credentials=True,
    allow_methods=["*"],          # <-- GET, POST, PUT, etc.
    allow_headers=["*"],          # <-- Authorization, Content-Type, etc.
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

def compress_outlet_data(outlets):
    """Compress outlet data to fit more in context"""
    compressed = []
    for outlet in outlets:
        # Extract only essential info in compact format
        name = outlet.get('name', 'Unknown')
        address = outlet.get('address', 'Unknown')
        hours = outlet.get('operating_hours', 'Unknown')
        
        # Compress address (keep key location identifiers)
        address_short = extract_location_keywords(address)
        
        # Compress hours (extract closing time)
        closing_time = extract_closing_time(hours)
        
        compressed.append(f"{name}|{address_short}|{closing_time}")
    
    return compressed

def extract_location_keywords(address):
    """Extract key location identifiers from address"""
    if not address:
        return "Unknown"
    
    # Common location keywords in Malaysia
    locations = ['Bangsar', 'KLCC', 'Mont Kiara', 'PJ', 'Subang', 'Damansara', 
                'Ampang', 'Cheras', 'KL', 'Selangor', 'Shah Alam']
    
    found_locations = [loc for loc in locations if loc.lower() in address.lower()]
    return found_locations[0] if found_locations else address[:20]

def extract_closing_time(hours):
    """Extract closing time from operating hours"""
    if not hours:
        return "Unknown"
    
    # Simple regex to find closing time patterns like "10PM", "22:00", etc.
    import re
    patterns = [
        r'(\d{1,2}:\d{2}\s*[AP]M)',
        r'(\d{1,2}[AP]M)',
        r'(\d{1,2}:\d{2})',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, hours.upper())
        if matches:
            return matches[-1]  # Return the last time (likely closing time)
    
    return hours[:10]  # Fallback to first 10 chars
@app.post("/chat-completion", response_model=ChatResponse)
def chat_completion(request: ChatRequest):
    try:
        outlets = get_all_outlets()
        query_lower = request.query.lower()
        
        # Try direct processing first for specific question types
        direct_answer = handle_direct_processing(request.query, outlets)
        if direct_answer:
            return ChatResponse(answer=direct_answer)
        
        # Fall back to LLM processing with optimized context
        return handle_llm_processing(request, outlets)
    except Exception as e:
        logger.error(f"Error in chat_completion: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat completion request")

def handle_direct_processing(query: str, outlets):
    """Handle questions that can be answered directly from data"""
    query_lower = query.lower()
    
    # Handle counting questions directly
    if any(word in query_lower for word in ['how many', 'count']):
        return handle_counting_directly(query_lower, outlets)
    
    # Handle latest closing time questions directly
    if any(phrase in query_lower for phrase in ['closes latest', 'latest closing']):
        return handle_latest_closing_directly(outlets)
    
    return None

def handle_counting_directly(query_lower: str, outlets):
    """Count outlets directly from data"""
    # Extract location from query
    locations = ['bangsar', 'klcc', 'mont kiara', 'pj', 'subang', 'damansara', 
                'ampang', 'cheras', 'shah alam', 'petaling jaya']
    
    target_location = None
    for loc in locations:
        if loc.replace(' ', '') in query_lower.replace(' ', ''):
            target_location = loc
            break
    
    if target_location:
        count = 0
        matching_outlets = []
        for outlet in outlets:
            address = outlet.get('address', '').lower()
            if target_location.replace(' ', '') in address.replace(' ', ''):
                count += 1
                matching_outlets.append(outlet.get('name', 'Unknown'))
        
        return f"{count} outlets in {target_location.title()}"
    
    return None

def handle_latest_closing_directly(outlets):
    """Find outlets with latest closing time directly"""
    import re
    from datetime import datetime
    
    outlet_times = []
    for outlet in outlets:
        name = outlet.get('name', 'Unknown')
        hours = outlet.get('operating_hours', '')
        
        # Extract closing time and convert to comparable format
        closing_time = extract_and_normalize_closing_time(hours)
        if closing_time:
            outlet_times.append((name, closing_time, hours))
    
    if not outlet_times:
        return "Closing times not available"
    
    # Sort by closing time
    outlet_times.sort(key=lambda x: x[1], reverse=True)
    latest_time = outlet_times[0][1]
    
    # Find all outlets with the latest time
    latest_outlets = [name for name, time, _ in outlet_times if time == latest_time]
    
    if len(latest_outlets) == 1:
        return f"{latest_outlets[0]} - Closes latest"
    else:
        return f"These outlets close latest: {', '.join(latest_outlets)}"

def extract_and_normalize_closing_time(hours_str):
    """Extract and normalize closing time for comparison"""
    if not hours_str:
        return None
    
    import re
    
    # Patterns to match different time formats
    patterns = [
        r'(\d{1,2}):(\d{2})\s*([AP]M)',  # 10:00 PM
        r'(\d{1,2})\s*([AP]M)',          # 10 PM
        r'(\d{1,2}):(\d{2})',            # 22:00
    ]
    
    times_found = []
    for pattern in patterns:
        matches = re.findall(pattern, hours_str.upper())
        for match in matches:
            if len(match) == 3:  # Hour, minute, AM/PM
                hour, minute, ampm = match
                hour = int(hour)
                minute = int(minute)
                if ampm == 'PM' and hour != 12:
                    hour += 12
                elif ampm == 'AM' and hour == 12:
                    hour = 0
                times_found.append(hour * 60 + minute)  # Convert to minutes for comparison
            elif len(match) == 2:
                if match[1] in ['AM', 'PM']:  # Hour, AM/PM
                    hour = int(match[0])
                    if match[1] == 'PM' and hour != 12:
                        hour += 12
                    elif match[1] == 'AM' and hour == 12:
                        hour = 0
                    times_found.append(hour * 60)
                else:  # Hour, minute (24-hour format)
                    hour, minute = int(match[0]), int(match[1])
                    times_found.append(hour * 60 + minute)
    
    return max(times_found) if times_found else None

def handle_llm_processing(request: ChatRequest, outlets):
    """Handle questions that need LLM processing with optimized context"""
    # Use compressed data approach
    compressed_outlets = compress_outlet_data(outlets)
    
    # Build context with compressed data
    context = f"""
Total outlets: {len(outlets)}

Outlet Data (Name|Location|Hours):
{chr(10).join(compressed_outlets)}
"""
    
    prompt = f"""
You are an assistant for outlet information. Use the outlet data below to answer the user's question.

{context}

User Question: {request.query}

Instructions:
- Answer based on the outlet data provided
- Be concise and direct
- If counting, provide exact numbers
- If asking about specific outlets, list their names

Answer:
"""
    
    # Call Groq API
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