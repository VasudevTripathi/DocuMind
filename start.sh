#!/usr/bin/env bash
set -e

# Run backend start script from root
exec "$(dirname "$0")/backend/start.sh"
