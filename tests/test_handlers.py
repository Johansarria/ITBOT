# tests/test_handlers.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update, User, Message, Chat, CallbackQuery
from telegram.ext import ContextTypes

from handlers import escape_markdown
import keyboards
