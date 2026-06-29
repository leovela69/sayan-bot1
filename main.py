# -*- coding: utf-8 -*-
"""
SAYAN BOT — Entry point
@Sayanyin_Bot — Bot autónomo independiente
"""
import sys
import os
import logging

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from src.platforms.telegram import run_telegram_bot

if __name__ == "__main__":
    print("SAYAN BOT v1.0 — Starting...")
    run_telegram_bot()
