#!/usr/bin/env python3
"""
CNC Pro - Sistema Profissional de Geração de G-code
Desenvolvido com PySide6 e Python
"""

import sys
import os
import logging
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import main

if __name__ == "__main__":
    main()