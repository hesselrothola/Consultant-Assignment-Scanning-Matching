"""
Web scrapers for Swedish consulting assignment portals.
"""

from .base import BaseScraper
from .brainville import BrainvilleScraper
from .cinode import CinodeScraper

__all__ = [
    'BaseScraper',
    'BrainvilleScraper',
    'CinodeScraper',
]