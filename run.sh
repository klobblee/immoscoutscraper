#!/usr/bin/env bash
exec /run/current-system/sw/bin/nix-shell \
  -p python3Packages.requests \
  -p python3Packages.beautifulsoup4 \
  -p python3Packages.lxml \
  -p python3Packages.pyyaml \
  -p python3Packages.schedule \
  --run "python3 /home/zeus/Documents/immoScoutScraper/main.py"
