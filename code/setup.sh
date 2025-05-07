#!/usr/bin/env bash
SCRIPT_PATH="$(readlink -f "$0")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"

cp "$SCRIPT_DIR/.env.template" "$SCRIPT_DIR/.env"