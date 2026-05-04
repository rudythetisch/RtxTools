#!/bin/bash
# Script to safely shut down the Nipogi server (Proxmox) via SSH

echo "Starting Nipogi shutdown process..."

# Load credentials
source "$(dirname "$0")/credentials.env"

echo "Connecting to Proxmox host at $NIPOGI_IP..."

ssh -o "PasswordAuthentication=no" "$NIPOGI_USER@$NIPOGI_IP" << 'REMOTE'
  echo "Stopping all virtual machines..."
  qm list | awk 'NR>1 {print $1}' | while read vmid; do
    echo "Stopping VM ID: $vmid"
    qm shutdown "$vmid" --timeout 60
  done

  echo "Waiting for VMs to stop..."
  sleep 10

  echo "Stopping Proxmox services..."
  systemctl stop pve-cluster pvedaemon pveproxy pvestatd

  echo "Shutting down the Nipogi server..."
  shutdown -h now
REMOTE

echo "Shutdown sequence initiated on Nipogi."
