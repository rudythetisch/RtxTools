# pfSense Firewall Commands for Parental Control

This document explains the pfSense firewall commands used in the parental control system.

## Command Overview

The system uses pfSense's `pfctl` command with anchors to dynamically manage firewall rules for blocking kids' devices.

### Enable Internet Access (Unblock)
```bash
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "pfctl -a kids_block -F rules"
```

**What it does:**
- Connects to pfSense via SSH
- Flushes (removes) all rules from the `kids_block` anchor
- Allows normal internet access for all devices

### Disable Internet Access (Block)
```bash
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "echo \"block out quick from <KID_DEVICES> to any\" | pfctl -a kids_block -f -"
```

**What it does:**
- Creates a blocking rule for the KID_DEVICES alias
- Blocks outbound traffic from kids' devices to any destination
- Keeps local network access intact

### Check Current Status
```bash
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "pfctl -a kids_block -s rules"
```

**What it does:**
- Shows current rules in the kids_block anchor
- Empty output = internet access allowed
- Rule output = internet access blocked

## Alternative Command Methods

### Method 1: Using pfSense Rule Management (Recommended)

If you prefer to use pfSense's built-in rule management instead of pfctl anchors:

1. **Create a firewall rule in pfSense web interface:**
   - Action: Block
   - Interface: LAN
   - Source: KID_DEVICES (alias)
   - Destination: WAN networks
   - Description: "Block Kids Internet Access"
   - **Important:** Disable the rule by default

2. **Use these commands instead:**

Enable internet (disable rule):
```bash
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "/usr/local/bin/pfSsh.php playback disablerule 0 'Block Kids Internet Access'"
```

Disable internet (enable rule):
```bash
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "/usr/local/bin/pfSsh.php playback enablerule 0 'Block Kids Internet Access'"
```

### Method 2: Using pfSense API (Advanced)

If you have the pfSense API package installed:

1. Install pfSense-pkg-API package
2. Configure API access
3. Use REST API calls instead of SSH commands

## Firewall Rule Logic

### What Gets Blocked
- **Outbound internet traffic** from kids' devices
- **DNS queries** to external servers (forces local DNS)
- **All WAN-bound traffic** from KID_DEVICES alias

### What Remains Accessible
- **Local network resources** (192.168.x.x, 10.x.x.x, etc.)
- **Local DNS server** (your pfSense/router)
- **Local file shares, printers, media servers**
- **Nintendo Switch local multiplayer**
- **Device management** (you can still ping/access the devices)

## Troubleshooting Commands

### Check if KID_DEVICES alias exists:
```bash
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "pfctl -t KID_DEVICES -T show"
```

### View all pfctl anchors:
```bash
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "pfctl -s Anchors"
```

### Check pfctl status:
```bash
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "pfctl -s info"
```

### View current firewall state:
```bash
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "pfctl -s state | grep -E '(192.168.1.100|192.168.1.101)'"
```
*Replace IPs with your kids' device IPs*

## Security Considerations

### SSH Key Security
- Private key stored in `/config/ssh_keys/pfsense_key`
- Key should have restrictive permissions (600)
- Consider using a dedicated pfSense user for Home Assistant

### Command Validation
- Commands are executed with admin privileges
- SSH connection uses key-based authentication
- StrictHostKeyChecking disabled for automation

### Firewall Impact
- Rules are temporary and don't persist across pfSense reboots
- No permanent changes to pfSense configuration
- Can be manually overridden from pfSense web interface

## Testing the Setup

### 1. Test SSH Connection
```bash
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "echo 'Connection successful'"
```

### 2. Test Block Command
```bash
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "echo \"block out quick from <KID_DEVICES> to any\" | pfctl -a kids_block -f -"
```

### 3. Test Unblock Command
```bash
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "pfctl -a kids_block -F rules"
```

### 4. Verify from Kids' Device
- Try accessing a website
- Check if local network resources still work
- Test Nintendo Switch online vs local multiplayer

## Common Issues and Solutions

### Issue: "pfctl: anchor not found"
**Solution:** pfSense might not support the anchor method. Use the rule management method instead.

### Issue: "Permission denied"
**Solution:** Ensure the SSH user has admin privileges in pfSense.

### Issue: "Connection refused"
**Solution:** Check if SSH is enabled in pfSense (System > Advanced > Admin Access).

### Issue: Commands work but devices still have internet
**Solution:** 
- Verify KID_DEVICES alias contains correct IP addresses
- Check if devices are using VPN or alternative DNS
- Ensure devices are getting IPs from your DHCP server

### Issue: Local network access also blocked
**Solution:** The rule might be too broad. Ensure you're blocking "to any" not "to !LAN_SUBNET".

## Monitoring and Logging

### Enable pfSense Logging
1. Go to Status > System Logs > Firewall
2. Enable logging for the blocking rule
3. Monitor logs when testing

### Home Assistant Logging
Add to Home Assistant `configuration.yaml`:
```yaml
logger:
  logs:
    homeassistant.components.shell_command: debug
```

This will log all shell command executions for troubleshooting.