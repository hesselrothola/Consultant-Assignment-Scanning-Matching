"""
Web scrapers for Swedish consulting assignment portals.
"""

from .base import BaseScraper
from .brainville import BrainvilleScraper

__all__ = [
    'BaseScraper',
    'BrainvilleScraper',
]