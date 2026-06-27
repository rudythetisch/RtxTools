#!/bin/bash
cd "$(dirname "$0")"
echo "Starting Homelab Dashboard..."
echo "  Express API : http://localhost:8160"
echo "  React UI    : http://localhost:5173 (dev) or http://localhost:8160 (prod)"
npm run dev
