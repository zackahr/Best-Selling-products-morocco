#!/bin/bash
set -euo pipefail

PROJECT="/Users/mac/Documents/avito-scrape"
LOG="$PROJECT/logs/scraper.log"

mkdir -p "$PROJECT/logs"

echo "--- $(date '+%Y-%m-%d %H:%M:%S') scrape start ---" >> "$LOG"
cd "$PROJECT"
python3 market_runner.py >> "$LOG" 2>&1
echo "--- $(date '+%Y-%m-%d %H:%M:%S') scrape done ---" >> "$LOG"
