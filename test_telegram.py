import asyncio
import os
import pytest
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.exceptions import TelegramUnauthorizedError, TelegramNetworkError

@pytest.mark.asyncio
async def test_token():
    """
    Tests the Telegram bot token by fetching the bot's information.
    """
    load_dotenv()
    token = os.getenv("TELEGRAM_TOKEN")

    if not token:
        print("❌ Error: TELEGRAM_TOKEN not found in .env file.")
        return

    print(f"🔑 Token found. Testing connection for bot...")

    try:
        bot = Bot(token=token)
        bot_info = await bot.get_me()
        print("✅ --- SUCCESS --- ✅")
        print(f"Bot ID: {bot_info.id}")
        print(f"Bot Name: {bot_info.full_name}")
        print(f"Bot Username: @{bot_info.username}")
        print("Your token is valid and the connection to Telegram is working.")
        await bot.session.close()

    except TelegramUnauthorizedError:
        print("❌ --- FAILURE --- ❌")
        print("Error: Unauthorized. Your TELEGRAM_TOKEN is incorrect or revoked.")
        print("Please check your .env file and make sure the token is correct.")
        print("You can get a new token from @BotFather on Telegram.")

    except TelegramNetworkError as e:
        print("❌ --- FAILURE --- ❌")
        print(f"Error: Network issue. Could not connect to Telegram.")
        print(f"Details: {e}")
        print("Please check your internet connection, firewall, or proxy settings.")

    except Exception as e:
        print(f"❌ --- FAILURE --- ❌")
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_token())