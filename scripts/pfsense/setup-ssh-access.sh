#!/bin/bash

# pfSense SSH Access Setup Script
# This script helps set up SSH access from Home Assistant to pfSense

echo "=== pfSense SSH Access Setup ==="
echo ""

# Check if we're running from Home Assistant container/system
if [ ! -d "/config" ]; then
    echo "Warning: This script should be run from Home Assistant system"
    echo "Creating /config directory for demonstration..."
    mkdir -p /config/ssh_keys
fi

# Create SSH keys directory
mkdir -p /config/ssh_keys
chmod 700 /config/ssh_keys

echo "1. Generating SSH key pair..."
ssh-keygen -t rsa -b 4096 -f /config/ssh_keys/pfsense_key -N "" -C "homeassistant-pfsense"

if [ $? -eq 0 ]; then
    echo "✓ SSH key pair generated successfully"
    echo "  Private key: /config/ssh_keys/pfsense_key"
    echo "  Public key: /config/ssh_keys/pfsense_key.pub"
else
    echo "✗ Failed to generate SSH key pair"
    exit 1
fi

# Set proper permissions
chmod 600 /config/ssh_keys/pfsense_key
chmod 644 /config/ssh_keys/pfsense_key.pub

echo ""
echo "2. Public key content (copy this to pfSense):"
echo "=============================================="
cat /config/ssh_keys/pfsense_key.pub
echo "=============================================="
echo ""

echo "3. pfSense Configuration Steps:"
echo "   a) Log into pfSense web interface"
echo "   b) Go to System > User Manager"
echo "   c) Edit the 'admin' user (or create a dedicated user)"
echo "   d) Paste the public key above into 'Authorized SSH Keys' field"
echo "   e) Save the configuration"
echo ""

echo "4. Enable SSH in pfSense:"
echo "   a) Go to System > Advanced > Admin Access"
echo "   b) Check 'Enable Secure Shell'"
echo "   c) Set SSH port (default 22)"
echo "   d) Save configuration"
echo ""

echo "5. Test SSH connection:"
echo "   Replace PFSENSE_IP with your actual pfSense IP address"
echo "   ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP"
echo ""

# Create a test script
cat > /config/ssh_keys/test-connection.sh << 'EOF'
#!/bin/bash
# Test SSH connection to pfSense
# Usage: ./test-connection.sh PFSENSE_IP

if [ -z "$1" ]; then
    echo "Usage: $0 <pfsense_ip>"
    exit 1
fi

PFSENSE_IP=$1
SSH_KEY="/config/ssh_keys/pfsense_key"

echo "Testing SSH connection to pfSense at $PFSENSE_IP..."

# Test basic connection
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$SSH_KEY" admin@"$PFSENSE_IP" "echo 'SSH connection successful'"

if [ $? -eq 0 ]; then
    echo "✓ SSH connection test passed"
    
    echo "Testing pfctl commands..."
    
    # Test pfctl command
    ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" admin@"$PFSENSE_IP" "pfctl -s info | head -5"
    
    if [ $? -eq 0 ]; then
        echo "✓ pfctl command test passed"
        echo "Setup appears to be working correctly!"
    else
        echo "✗ pfctl command test failed"
        echo "Check pfSense user permissions"
    fi
else
    echo "✗ SSH connection test failed"
    echo "Check:"
    echo "  - pfSense IP address"
    echo "  - SSH is enabled in pfSense"
    echo "  - Public key is added to pfSense user"
    echo "  - Network connectivity"
fi
EOF

chmod +x /config/ssh_keys/test-connection.sh

echo "6. Test script created: /config/ssh_keys/test-connection.sh"
echo "   Run: /config/ssh_keys/test-connection.sh YOUR_PFSENSE_IP"
echo ""

echo "Setup complete! Next steps:"
echo "1. Configure pfSense as described above"
echo "2. Test the connection using the test script"
echo "3. Update the pfsense_ip in Home Assistant configuration"
echo "4. Restart Home Assistant to load the new configuration"