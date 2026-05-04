#!/bin/bash
# Script to safely shut down a Synology NAS via SSH

# Preserve env vars passed externally (e.g. from web server) before sourcing credentials
_NAS_IP="$NAS_IP"
_NAS_USER="$NAS_USER"

# Load credentials as defaults
source "$(dirname "$0")/credentials.env"

# External env vars take precedence over file values
[ -n "$_NAS_IP" ] && NAS_IP="$_NAS_IP"
[ -n "$_NAS_USER" ] && NAS_USER="$_NAS_USER"

echo "Starting shutdown process for Synology NAS at $NAS_IP..."
ssh -o "PasswordAuthentication=no" "$NAS_USER@$NAS_IP" "sudo synoshutdown --now"
echo "Shutdown command sent to Synology NAS at $NAS_IP."
