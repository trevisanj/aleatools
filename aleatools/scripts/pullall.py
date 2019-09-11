#!/usr/bin/env python3
"""Pulls repositories using git."""

import logging
import a107
import aleatools

SIMULATION = False

if __name__ == "__main__":
    aleatools.gitaux_main(False, SIMULATION)
