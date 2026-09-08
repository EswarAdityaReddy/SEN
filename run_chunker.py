"""
Root execution script for SEN Vector RAG Chunker.
Run python run_chunker.py to process all files in sen_data/ and build RAG chunks.
"""

import os
import sys
from sen_chunker.cli import main

if __name__ == "__main__":
    main()
