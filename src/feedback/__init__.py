"""
Feedback module for collecting and processing user feedback
"""

from .collector import FeedbackCollector, FeedbackType, get_feedback_collector

__all__ = ['FeedbackCollector', 'FeedbackType', 'get_feedback_collector']
