from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from decimal import Decimal
import logging
from difflib import SequenceMatcher

from app.models import Job, Consultant, JobConsultantMatch, MatchReason
from app.repo import DatabaseRepository
from app.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class MatchingService:
    # Weights for different matching components
    WEIGHT_COSINE = 0.45
    WEIGHT_SKILLS = 0.25
    WEIGHT_ROLE = 0.15
    WEIGHT_LANGUAGE = 0.10
    WEIGHT_GEO = 0.05
    
    def __init__(self, db_repo: DatabaseRepository, embedding_service: EmbeddingService):
        self.db = db_repo
        self.embeddings = embedding_service
    
    async def run_matching(
        self,
        job_ids: Optional[List[UUID]] = None,
        consultant_ids: Optional[List[UUID]] = None,
        min_score: float = 0.5,
        max_results: int = 10
    ) -> List[JobConsultantMatch]:
        """Run matching algorithm for specified jobs and consultants."""
        
        # Get jobs to match
        if job_ids:
            jobs = [await self.db.get_job(job_id) for job_id in job_ids]
            jobs = [j for j in jobs if j]
        else:
            # Get recent jobs
            jobs = await self.db.get_jobs(limit=100)
        
        # Get consultants to match
        if consultant_ids:
            consultants = [await self.db.get_consultant(c_id) for c_id in consultant_ids]
            consultants = [c for c in consultants if c]
        else:
            # Get all active consultants
            consultants = await self.db.get_consultants(active_only=True, limit=100)
        
        matches = []
        
        for job in jobs:
            job_matches = await self._match_job_to_consultants(
                job, consultants, min_score, max_results
            )
            matches.extend(job_matches)
        
        return matches
    
    async def _match_job_to_consultants(
        self,
        job: Job,
        consultants: List[Consultant],
        min_score: float,
        max_results: int
    ) -> List[JobConsultantMatch]:
        """Match a single job to multiple consultants."""
        
        # Get job embedding
        job_embedding = await self.db.get_job_embedding(job.job_id)
        if not job_embedding:
            # Create embedding if not exists
            job_text = self.embeddings.prepare_job_text(job.model_dump())
            job_embedding = await self.embeddings.create_embedding(job_text)
            await self.db.store_job_embedding(job.job_id, job_embedding)
        
        scored_matches = []
        
        for consultant in consultants:
            # Get consultant embedding
            consultant_embedding = await self.db.get_consultant_embedding(consultant.consultant_id)
            if not consultant_embedding:
                # Create embedding if not exists
                consultant_text = self.embeddings.prepare_consultant_text(consultant.model_dump())
                consultant_embedding = await self.embeddings.create_embedding(consultant_text)
                await self.db.store_consultant_embedding(consultant.consultant_id, consultant_embedding)
            
            # Calculate match scores
            scores = self._calculate_match_scores(job, consultant, job_embedding, consultant_embedding)
            
            if scores['total'] >= min_score:
                reason = self._generate_match_reason(job, consultant, scores)
                scored_matches.append((consultant, scores, reason))
        
        # Sort by total score and take top results
        scored_matches.sort(key=lambda x: x[1]['total'], reverse=True)
        top_matches = scored_matches[:max_results]
        
        # Store matches in database
        matches = []
        for consultant, scores, reason in top_matches:
            match = await self.db.upsert_match(
                job_id=job.job_id,
                consultant_id=consultant.consultant_id,
                score=scores['total'],
                reason_json=reason.model_dump()
            )
            matches.append(match)
        
        return matches
    
    def _calculate_match_scores(
        self,
        job: Job,
        consultant: Consultant,
        job_embedding: List[float],
        consultant_embedding: List[float]
    ) -> Dict[str, float]:
        """Calculate all matching scores between job and consultant."""
        
        # Cosine similarity
        cosine_score = self.embeddings.cosine_similarity(job_embedding, consultant_embedding)
        
        # Skills match
        skills_score = self._calculate_skills_match(job.skills, consultant.skills)
        
        # Role match
        role_score = self._calculate_role_match(job, consultant)
        
        # Language match
        language_score = self._calculate_language_match(
            job.languages, consultant.languages
        )
        
        # Geographic match
        geo_score = self._calculate_geo_match(job, consultant)
        
        # Calculate weighted total
        total_score = (
            self.WEIGHT_COSINE * cosine_score +
            self.WEIGHT_SKILLS * skills_score +
            self.WEIGHT_ROLE * role_score +
            self.WEIGHT_LANGUAGE * language_score +
            self.WEIGHT_GEO * geo_score
        )
        
        return {
            'total': total_score,
            'cosine': cosine_score,
            'skills': skills_score,
            'role': role_score,
            'language': language_score,
            'geo': geo_score
        }
    
    def _calculate_skills_match(
        self,
        job_skills: List[str],
        consultant_skills: List[str]
    ) -> float:
        """Calculate skills matching score."""
        if not job_skills:
            return 1.0  # No skills required
        
        if not consultant_skills:
            return 0.0  # Skills required but consultant has none
        
        # Normalize skills for comparison
        job_skills_lower = [s.lower().strip() for s in job_skills]
        consultant_skills_lower = [s.lower().strip() for s in consultant_skills]
        
        matches = 0
        for job_skill in job_skills_lower:
            # Check exact match or fuzzy match
            for consultant_skill in consultant_skills_lower:
                if job_skill == consultant_skill:
                    matches += 1
                    break
                elif SequenceMatcher(None, job_skill, consultant_skill).ratio() > 0.8:
                    matches += 0.8  # Partial credit for fuzzy match
                    break
        
        return min(1.0, matches / len(job_skills_lower))
    
    def _calculate_role_match(self, job: Job, consultant: Consultant) -> float:
        """Calculate role/seniority matching score."""
        # Direct seniority match if both have it
        if job.seniority and consultant.seniority:
            job_sen = job.seniority.lower()
            cons_sen = consultant.seniority.lower()
            
            # Exact match
            if job_sen == cons_sen:
                return 1.0
            
            # Close matches
            senior_terms = ['senior', 'lead', 'principal', 'architect', 'expert']
            mid_terms = ['mid', 'intermediate', 'experienced', 'regular']
            junior_terms = ['junior', 'entry', 'trainee', 'intern', 'graduate']
            
            job_is_senior = any(term in job_sen for term in senior_terms)
            job_is_mid = any(term in job_sen for term in mid_terms)
            job_is_junior = any(term in job_sen for term in junior_terms)
            
            cons_is_senior = any(term in cons_sen for term in senior_terms)
            cons_is_mid = any(term in cons_sen for term in mid_terms)
            cons_is_junior = any(term in cons_sen for term in junior_terms)
            
            if (job_is_senior and cons_is_senior) or \
               (job_is_mid and cons_is_mid) or \
               (job_is_junior and cons_is_junior):
                return 0.9
            elif (job_is_senior and cons_is_mid) or \
                 (job_is_mid and cons_is_senior):
                return 0.6
            else:
                return 0.3
        
        # Role-based matching if seniority not available
        if job.role and consultant.role:
            if job.role.lower() == consultant.role.lower():
                return 0.8
            # Check for similar roles using canonical roles
            return 0.5
        
        return 0.5  # Neutral if no data
    
    def _calculate_language_match(
        self,
        job_languages: List[str],
        consultant_languages: List[str]
    ) -> float:
        """Calculate language requirements matching score."""
        if not job_languages:
            return 1.0  # No language requirements
        
        if not consultant_languages:
            return 0.0  # Languages required but consultant has none listed
        
        job_langs_lower = [l.lower().strip() for l in job_languages]
        consultant_langs_lower = [l.lower().strip() for l in consultant_languages]
        
        matches = sum(1 for lang in job_langs_lower if lang in consultant_langs_lower)
        
        return matches / len(job_langs_lower)
    
    def _calculate_geo_match(
        self,
        job: Job,
        consultant: Consultant
    ) -> float:
        """Calculate geographic matching score."""
        # Check onsite mode compatibility first
        if job.onsite_mode and consultant.onsite_mode:
            if job.onsite_mode == 'remote' or consultant.onsite_mode == 'remote':
                return 0.9  # Remote work makes location less important
            elif job.onsite_mode == 'hybrid' and consultant.onsite_mode in ['hybrid', 'onsite']:
                base_score = 0.7
            elif job.onsite_mode == consultant.onsite_mode:
                base_score = 0.8
            else:
                base_score = 0.3
        else:
            base_score = 0.5
        
        # Location matching
        if job.location_city and consultant.location_city:
            job_city = job.location_city.lower()
            cons_city = consultant.location_city.lower()
            
            # Exact city match
            if job_city == cons_city:
                return min(1.0, base_score + 0.3)
            
            # Same region check for Swedish cities
            swedish_regions = {
                'stockholm': ['stockholm', 'solna', 'sundbyberg', 'täby', 'nacka', 'järfälla'],
                'gothenburg': ['gothenburg', 'göteborg', 'mölndal', 'partille', 'kungsbacka'],
                'malmö': ['malmö', 'lund', 'helsingborg', 'landskrona', 'eslöv'],
                'uppsala': ['uppsala', 'enköping', 'knivsta', 'östhammar']
            }
            
            job_region = None
            cons_region = None
            
            for region, cities in swedish_regions.items():
                if any(city in job_city for city in cities):
                    job_region = region
                if any(city in cons_city for city in cities):
                    cons_region = region
            
            if job_region and cons_region and job_region == cons_region:
                return min(1.0, base_score + 0.2)
        
        # Country match
        if job.location_country and consultant.location_country:
            if job.location_country.lower() == consultant.location_country.lower():
                return min(1.0, base_score + 0.1)
        
        return base_score
    
    def _generate_match_reason(
        self,
        job: Job,
        consultant: Consultant,
        scores: Dict[str, float]
    ) -> MatchReason:
        """Generate human-readable reason for the match."""
        
        # Find matched and missing skills
        job_skills_lower = [s.lower() for s in job.skills] if job.skills else []
        consultant_skills_lower = [s.lower() for s in consultant.skills] if consultant.skills else []
        
        skills_matched = []
        skills_missing = []
        
        for skill in job_skills_lower:
            if skill in consultant_skills_lower:
                skills_matched.append(skill)
            else:
                # Check for fuzzy match
                fuzzy_matched = False
                for c_skill in consultant_skills_lower:
                    if SequenceMatcher(None, skill, c_skill).ratio() > 0.8:
                        skills_matched.append(f"{skill} (~{c_skill})")
                        fuzzy_matched = True
                        break
                if not fuzzy_matched:
                    skills_missing.append(skill)
        
        # Language match
        language_match = scores['language'] >= 0.8
        
        # Location match
        location_match = scores['geo'] >= 0.6
        
        # Availability match (simplified)
        availability_match = True  # Could be enhanced with date comparison
        
        # Rate match (if data available)
        rate_match = True
        if job.hourly_rate_max and consultant.hourly_rate:
            rate_match = consultant.hourly_rate <= job.hourly_rate_max
        
        # Generate strengths and concerns
        strengths = []
        concerns = []
        
        if scores['cosine'] >= 0.7:
            strengths.append("Strong overall profile match")
        
        if scores['skills'] >= 0.8:
            strengths.append(f"Excellent skills match ({len(skills_matched)}/{len(job_skills_lower)} skills)")
        elif scores['skills'] >= 0.6:
            strengths.append(f"Good skills match ({len(skills_matched)}/{len(job_skills_lower)} skills)")
        else:
            concerns.append(f"Limited skills match ({len(skills_matched)}/{len(job_skills_lower)} skills)")
        
        if scores['role'] >= 0.8:
            strengths.append("Perfect seniority level match")
        elif scores['role'] <= 0.3:
            concerns.append("Seniority level mismatch")
        
        if language_match:
            strengths.append("Meets language requirements")
        else:
            concerns.append("May not meet all language requirements")
        
        if location_match:
            strengths.append("Good location match")
        elif scores['geo'] <= 0.3:
            concerns.append("Location mismatch")
        
        if consultant.availability_date:
            strengths.append(f"Available from {consultant.availability_date}")
        
        # Generate summary
        summary = f"Match score: {scores['total']:.2%}. "
        if scores['total'] >= 0.8:
            summary += "Excellent candidate for this position."
        elif scores['total'] >= 0.6:
            summary += "Good candidate worth considering."
        else:
            summary += "Potential candidate with some gaps."
        
        return MatchReason(
            summary=summary,
            skills_matched=skills_matched,
            skills_missing=skills_missing,
            language_match=language_match,
            location_match=location_match,
            availability_match=availability_match,
            rate_match=rate_match,
            strengths=strengths,
            concerns=concerns
        )