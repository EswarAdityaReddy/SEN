"""
CLI interface for running SEN document chunking pipeline.
"""

import os
import sys
import argparse
from .pipeline import run_chunking_pipeline

def main():
    parser = argparse.ArgumentParser(description="SEN Document & Dataset Chunking Pipeline")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=os.path.join(os.getcwd(), "sen_data"),
        help="Path to sen_data directory containing raw, extracted, and metadata folders"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom directory for processed chunk JSON outputs"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Target specific year to chunk (2010..2026)"
    )

    args = parser.parse_args()

    if not os.path.exists(args.data_dir):
        print(f"Error: Data directory '{args.data_dir}' does not exist.")
        sys.exit(1)

    run_chunking_pipeline(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        target_year=args.year
    )

if __name__ == "__main__":
    main()
