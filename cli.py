#!/usr/bin/env python3
"""
SportDesk CLI - Interactive Terminal Assistant for Sports Event Management
"""

import sys
from engine.nlp import engine
from engine.event_db import init_db

# ANSI Color codes for clean terminal output
BLUE = "\033[94m"
GREEN = "\033[92m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_banner():
    print(f"\n{BLUE}{BOLD}=================================================={RESET}")
    print(f"{BLUE}{BOLD}          SportDesk - Event Assistant             {RESET}")
    print(f"{GRAY}   Lightweight NLTK & SQLite Sports Event Engine  {RESET}")
    print(f"{BLUE}{BOLD}=================================================={RESET}")
    print(f"{GRAY}Type your query below. Type 'exit' or 'quit' to close.\n{RESET}")

def main():
    init_db()
    print_banner()

    while True:
        try:
            query = input(f"{BOLD}You:{RESET} ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", "q"):
                print(f"\n{GRAY}Exiting SportDesk. Have a great event!{RESET}\n")
                break

            result = engine.predict(query)
            response = result["response"]
            source = result.get("source", "General")
            confidence = result.get("confidence", 0.0)

            print(f"\n{BLUE}{BOLD}SportDesk:{RESET} {response}")
            print(f"{GRAY}[Source: {source} | Confidence: {confidence}]{RESET}\n")

        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{GRAY}Exiting SportDesk.{RESET}\n")
            sys.exit(0)

if __name__ == "__main__":
    main()
