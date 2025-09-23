"""
Web scrapers for Swedish consulting assignment portals.
"""

from .base import BaseScraper
from .brainville import BrainvilleScraper
from .cinode import CinodeScraper
from .ework import EworkScraper

__all__ = [
    'BaseScraper',
    'BrainvilleScraper',
    'CinodeScraper',
    'EworkScraper',
]