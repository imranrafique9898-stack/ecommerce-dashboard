"""
run.py — Single entry point for all operations.

Commands:
  python run.py scrape       Start / resume scraping all categories
  python run.py patch        Patch missing seller feedback % on existing items
  python run.py export       Export collected data to CSV
  python run.py view         Live results viewer (auto-refreshes every 5s)
  python run.py view once    One-time snapshot
  python run.py stats        Show collection stats
"""

import sys

COMMANDS = ["scrape", "patch", "export", "view", "stats"]

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    if cmd == "scrape":
        from scraper import main as run
        run()

    elif cmd == "patch":
        from scraper import patch_feedback
        patch_feedback()

    elif cmd == "export":
        from scraper import export_csv
        export_csv()

    elif cmd == "view":
        from scraper import view_results
        view_results(once=(len(sys.argv) > 2 and sys.argv[2] == "once"))

    elif cmd == "stats":
        from scraper import show_stats
        show_stats()

    else:
        print(__doc__)

if __name__ == "__main__":
    main()
