import os
from typing import List, Optional
import numpy as np
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.backend = os.getenv("EMBEDDING_BACKEND", "local")
        if self.backend == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = AsyncOpenAI(api_key=api_key)
                self.model_version = "text-embedding-3-small"
            else:
                logger.warning("OPENAI_API_KEY not set, falling back to local embeddings")
                self.backend = "local"
        
        if self.backend == "local":
            self.client = None
            self.model_version = "local"
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding for a single text."""
        if not text:
            return []
        
        if self.backend == "openai" and self.client:
            try:
                response = await self.client.embeddings.create(
                    model=self.model_version,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error(f"OpenAI embedding error: {e}")
                raise
        else:
            # Simple local embedding - deterministic vector from text
            import hashlib
            text_hash = hashlib.sha256(text.encode()).digest()
            # Create a 1536-dimensional vector
            embedding = []
            for i in range(192):  # 192 * 8 = 1536
                chunk = text_hash[i % 32]
                for j in range(8):
                    embedding.append((chunk >> j & 1) * 0.5 - 0.25)
            return embedding[:1536]
    
    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for multiple texts."""
        if self.backend == "openai" and self.client:
            try:
                response = await self.client.embeddings.create(
                    model=self.model_version,
                    input=texts
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                logger.error(f"OpenAI embedding error: {e}")
                raise
        else:
            # Use single embedding method for each text
            embeddings = []
            for text in texts:
                embeddings.append(await self.create_embedding(text))
            return embeddings
    
    def prepare_job_text(self, job_data: dict) -> str:
        """Prepare job data for embedding."""
        parts = []
        
        if job_data.get('title'):
            parts.append(f"Title: {job_data['title']}")
        
        if job_data.get('role'):
            parts.append(f"Role: {job_data['role']}")
        
        if job_data.get('seniority'):
            parts.append(f"Seniority: {job_data['seniority']}")
        
        if job_data.get('description'):
            parts.append(f"Description: {job_data['description']}")
        
        if job_data.get('skills'):
            skills = job_data['skills'] if isinstance(job_data['skills'], list) else [job_data['skills']]
            parts.append(f"Skills: {', '.join(skills)}")
        
        if job_data.get('languages'):
            langs = job_data['languages'] if isinstance(job_data['languages'], list) else [job_data['languages']]
            parts.append(f"Languages: {', '.join(langs)}")
        
        if job_data.get('location_city'):
            parts.append(f"City: {job_data['location_city']}")
        
        if job_data.get('location_country'):
            parts.append(f"Country: {job_data['location_country']}")
        
        if job_data.get('onsite_mode'):
            parts.append(f"Work mode: {job_data['onsite_mode']}")
        
        if job_data.get('duration'):
            parts.append(f"Duration: {job_data['duration']}")
        
        return "\n".join(parts)
    
    def prepare_consultant_text(self, consultant_data: dict) -> str:
        """Prepare consultant data for embedding."""
        parts = []
        
        if consultant_data.get('name'):
            parts.append(f"Name: {consultant_data['name']}")
        
        if consultant_data.get('role'):
            parts.append(f"Role: {consultant_data['role']}")
        
        if consultant_data.get('seniority'):
            parts.append(f"Seniority: {consultant_data['seniority']}")
        
        if consultant_data.get('skills'):
            skills = consultant_data['skills'] if isinstance(consultant_data['skills'], list) else [consultant_data['skills']]
            parts.append(f"Skills: {', '.join(skills)}")
        
        if consultant_data.get('languages'):
            langs = consultant_data['languages'] if isinstance(consultant_data['languages'], list) else [consultant_data['languages']]
            parts.append(f"Languages: {', '.join(langs)}")
        
        if consultant_data.get('location_city'):
            parts.append(f"City: {consultant_data['location_city']}")
        
        if consultant_data.get('location_country'):
            parts.append(f"Country: {consultant_data['location_country']}")
        
        if consultant_data.get('onsite_mode'):
            parts.append(f"Work mode: {consultant_data['onsite_mode']}")
        
        if consultant_data.get('notes'):
            # Truncate notes if too long
            notes_text = consultant_data['notes'][:2000] if consultant_data.get('notes') and len(consultant_data['notes']) > 2000 else consultant_data.get('notes', '')
            if notes_text:
                parts.append(f"Notes: {notes_text}")
        
        return "\n".join(parts)
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0
        
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))