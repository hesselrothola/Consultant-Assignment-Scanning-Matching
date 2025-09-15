"""
AI-powered CV parser for extracting consultant information from uploaded CVs.
Supports PDF, DOCX, and text files.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import openai
import PyPDF2
import docx
import asyncio
from pathlib import Path

from app.config import settings
from app.models import ConsultantCreate, OnsiteMode

logger = logging.getLogger(__name__)


class CVParser:
    """Parse CVs using AI to extract structured consultant information."""
    
    def __init__(self):
        """Initialize the CV parser with OpenAI client."""
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required for CV parsing")
        
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    async def parse_cv_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a CV file and extract consultant information.
        
        Args:
            file_path: Path to the CV file (PDF, DOCX, or TXT)
            
        Returns:
            Dictionary with extracted consultant information
        """
        # Extract text from file
        text_content = await self._extract_text(file_path)
        
        if not text_content:
            raise ValueError("Could not extract text from CV file")
        
        # Use AI to parse the CV text
        parsed_data = await self._parse_with_ai(text_content)
        
        return parsed_data
    
    async def _extract_text(self, file_path: str) -> str:
        """Extract text content from various file formats."""
        file_extension = Path(file_path).suffix.lower()
        
        try:
            if file_extension == '.pdf':
                return await self._extract_pdf_text(file_path)
            elif file_extension in ['.docx', '.doc']:
                return await self._extract_docx_text(file_path)
            elif file_extension in ['.txt', '.text']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            raise
    
    async def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file."""
        text = ""
        
        def extract():
            nonlocal text
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        
        return await asyncio.to_thread(extract)
    
    async def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        def extract():
            doc = docx.Document(file_path)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        
        return await asyncio.to_thread(extract)
    
    async def _parse_with_ai(self, cv_text: str) -> Dict[str, Any]:
        """Use AI to parse CV text and extract structured information."""
        
        # Truncate very long CVs to fit in context
        max_chars = 10000
        if len(cv_text) > max_chars:
            cv_text = cv_text[:max_chars] + "... [truncated]"
        
        prompt = """Extract structured information from this CV for a consultant database.
        
Focus on extracting:
1. Personal Information (name, email, phone, location)
2. Current Role/Title
3. Seniority Level (Junior/Medior/Senior/Expert/Principal)
4. Years of Experience
5. Technical Skills (programming languages, frameworks, tools)
6. Languages Spoken
7. Preferred Work Mode (Onsite/Remote/Hybrid)
8. Hourly Rate Expectations (if mentioned)
9. Certifications
10. Industry Experience
11. Availability Date

Return a JSON with these fields:
{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "+46...",
    "location_city": "Stockholm",
    "location_country": "Sweden",
    "role": "Senior Backend Developer",
    "seniority": "Senior",
    "years_experience": 10,
    "skills": ["Python", "Django", "AWS", ...],
    "languages": ["Swedish", "English"],
    "onsite_preference": "HYBRID",
    "hourly_rate": 1200,
    "currency": "SEK",
    "certifications": ["AWS Certified", ...],
    "industries": ["FinTech", "E-commerce"],
    "availability_date": "2025-10-01",
    "bio": "Brief professional summary",
    "specializations": ["Cloud Architecture", "DevOps"]
}

If a field is not found, use null. Be accurate and extract real information only.

CV Content:
"""
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4o-mini",  # More capable for document parsing
                messages=[
                    {"role": "system", "content": "You are an expert CV parser for the Swedish IT consulting market. Extract accurate information from CVs."},
                    {"role": "user", "content": prompt + cv_text}
                ],
                temperature=0.1,  # Low temperature for accuracy
                max_tokens=2000,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            import json
            parsed_data = json.loads(response.choices[0].message.content)
            
            # Post-process the data
            return self._post_process_parsed_data(parsed_data)
            
        except Exception as e:
            logger.error(f"AI parsing failed: {e}")
            raise ValueError(f"Failed to parse CV with AI: {str(e)}")
    
    def _post_process_parsed_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate parsed data."""
        
        # Map onsite preference to enum
        onsite_map = {
            "REMOTE": OnsiteMode.REMOTE,
            "HYBRID": OnsiteMode.HYBRID,
            "ONSITE": OnsiteMode.ONSITE,
            "FLEXIBLE": OnsiteMode.HYBRID
        }
        
        if data.get("onsite_preference"):
            preference = data["onsite_preference"].upper()
            data["onsite_preference"] = onsite_map.get(preference, OnsiteMode.HYBRID).value
        
        # Ensure lists are lists
        for field in ["skills", "languages", "certifications", "industries", "specializations"]:
            if data.get(field) and not isinstance(data[field], list):
                data[field] = [data[field]]
        
        # Parse availability date
        if data.get("availability_date"):
            try:
                data["availability_date"] = datetime.fromisoformat(data["availability_date"])
            except:
                data["availability_date"] = None
        
        # Set defaults for missing fields
        defaults = {
            "location_country": "Sweden",
            "seniority": "Senior",
            "onsite_preference": OnsiteMode.HYBRID.value,
            "is_active": True,
            "languages": ["Swedish", "English"],
            "currency": "SEK"
        }
        
        for key, value in defaults.items():
            if not data.get(key):
                data[key] = value
        
        # Remove None values
        cleaned_data = {k: v for k, v in data.items() if v is not None}
        
        return cleaned_data
    
    def create_consultant_model(self, parsed_data: Dict[str, Any]) -> ConsultantCreate:
        """
        Convert parsed CV data to ConsultantCreate model.
        
        Args:
            parsed_data: Dictionary with parsed CV information
            
        Returns:
            ConsultantCreate model ready for database insertion
        """
        # Map parsed fields to model fields
        consultant_data = {
            "name": parsed_data.get("name", "Unknown"),
            "email": parsed_data.get("email"),
            "phone": parsed_data.get("phone"),
            "role": parsed_data.get("role", "Consultant"),
            "seniority": parsed_data.get("seniority", "Senior"),
            "skills": parsed_data.get("skills", []),
            "languages": parsed_data.get("languages", ["Swedish", "English"]),
            "location_city": parsed_data.get("location_city"),
            "location_country": parsed_data.get("location_country", "Sweden"),
            "onsite_preference": parsed_data.get("onsite_preference", OnsiteMode.HYBRID.value),
            "availability_date": parsed_data.get("availability_date"),
            "hourly_rate": parsed_data.get("hourly_rate"),
            "currency": parsed_data.get("currency", "SEK"),
            "bio": parsed_data.get("bio"),
            "years_experience": parsed_data.get("years_experience"),
            "certifications": parsed_data.get("certifications", []),
            "linkedin_url": parsed_data.get("linkedin_url"),
            "github_url": parsed_data.get("github_url"),
            "is_active": True
        }
        
        # Remove None values
        consultant_data = {k: v for k, v in consultant_data.items() if v is not None}
        
        return ConsultantCreate(**consultant_data)


async def parse_and_add_consultant(file_path: str, db_repo) -> Dict[str, Any]:
    """
    Parse a CV file and add the consultant to the database.
    
    Args:
        file_path: Path to the CV file
        db_repo: Database repository instance
        
    Returns:
        Dictionary with status and consultant information
    """
    try:
        parser = CVParser()
        
        # Parse the CV
        logger.info(f"Parsing CV file: {file_path}")
        parsed_data = await parser.parse_cv_file(file_path)
        
        # Create consultant model
        consultant_model = parser.create_consultant_model(parsed_data)
        
        # Check if consultant already exists (by email)
        if consultant_model.email:
            # Try to find existing consultant by email
            try:
                existing_consultants = await db_repo.get_consultants(limit=1000)
                existing = None
                for c in existing_consultants:
                    if c.email and c.email.lower() == consultant_model.email.lower():
                        existing = c
                        break
            except:
                existing = None
                
            if existing:
                logger.info(f"Consultant {consultant_model.name} already exists, updating...")
                # Update existing consultant
                consultant = await db_repo.update_consultant(
                    existing.consultant_id,
                    consultant_model.dict()
                )
                return {
                    "status": "updated",
                    "consultant": consultant,
                    "message": f"Updated existing consultant: {consultant.name}"
                }
        
        # Add new consultant
        consultant = await db_repo.create_consultant(consultant_model)
        logger.info(f"Added new consultant: {consultant.name}")
        
        return {
            "status": "created",
            "consultant": consultant,
            "message": f"Successfully added consultant: {consultant.name}"
        }
        
    except Exception as e:
        logger.error(f"Failed to parse and add consultant: {e}")
        return {
            "status": "error",
            "message": str(e)
        }