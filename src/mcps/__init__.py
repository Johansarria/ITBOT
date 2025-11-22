"""MCPs (Micro-Controller Processes) específicos de SICAR
"""

from .breakout_detector_mcp import BreakoutDetectorMCP
from .paper_trading_mcp import PaperTradingMCP

__all__ = ['BreakoutDetectorMCP', 'PaperTradingMCP']