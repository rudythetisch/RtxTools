# Parental Control Timer System - Installation Guide

This guide will walk you through installing and configuring the parental control timer system that integrates Home Assistant with pfSense.

## Prerequisites

- ✅ Home Assistant running in VM on Proxmox
- ✅ pfSense running in VM on Proxmox  
- ✅ KID_DEVICES alias configured in pfSense with children's device IPs
- ✅ Administrative access to both systems
- ✅ SSH access to Proxmox host

## Installation Steps

### Step 1: Backup Current Configurations

**Backup pfSense:**
1. Log into pfSense web interface
2. Go to Diagnostics > Backup & Restore
3. Download current configuration
4. Store backup file safely

**Backup Home Assistant:**
1. Go to Settings > System > Backups
2. Create a full backup
3. Download backup file

### Step 2: Set Up SSH Access

**On Home Assistant system:**

1. Access Home Assistant container/VM via SSH or console
2. Run the SSH setup script:
   ```bash
   # Copy the setup script to Home Assistant
   # Then run:
   chmod +x /config/scripts/pfsense/setup-ssh-access.sh
   /config/scripts/pfsense/setup-ssh-access.sh
   ```

3. Copy the generated public key (displayed by the script)

**On pfSense:**

1. Log into pfSense web interface
2. Go to **System > User Manager**
3. Edit the **admin** user (or create dedicated user)
4. Scroll to **Authorized SSH Keys**
5. Paste the public key from Step 2
6. Click **Save**

**Enable SSH in pfSense:**

1. Go to **System > Advanced**
2. Click **Admin Access** tab
3. Check **Enable Secure Shell**
4. Set SSH port (default: 22)
5. Click **Save**

**Test SSH Connection:**
```bash
# From Home Assistant
ssh -i /config/ssh_keys/pfsense_key admin@YOUR_PFSENSE_IP "echo 'Connection successful'"
```

### Step 3: Configure Home Assistant

**Add configuration sections:**

1. **Edit `configuration.yaml`:**
   - Copy content from [`scripts/home-assistant/configuration.yaml`](scripts/home-assistant/configuration.yaml)
   - Update `input_text.pfsense_ip` with your pfSense IP address
   - Update notification service names to match your mobile devices

2. **Add automations:**
   - Copy content from [`scripts/home-assistant/automations.yaml`](scripts/home-assistant/automations.yaml) 
   - Add to your existing automations.yaml or create new file

3. **Add scripts:**
   - Copy content from [`scripts/home-assistant/scripts.yaml`](scripts/home-assistant/scripts.yaml)
   - Add to your existing scripts.yaml or create new file

4. **Create dashboard:**
   - Copy content from [`scripts/home-assistant/dashboard.yaml`](scripts/home-assistant/dashboard.yaml)
   - Create new dashboard or add to existing one

### Step 4: Verify pfSense Configuration

**Check KID_DEVICES alias:**

1. Go to **Firewall > Aliases**
2. Verify **KID_DEVICES** alias exists
3. Confirm it contains correct IP addresses for children's devices
4. Example content:
   ```
   192.168.1.100  # Child 1 Android phone
   192.168.1.101  # Child 2 iPhone  
   192.168.1.102  # Child 3 iPad
   192.168.1.103  # Nintendo Switch
   ```

**Test firewall commands:**
```bash
# From Home Assistant, test blocking
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "echo \"block out quick from <KID_DEVICES> to any\" | pfctl -a kids_block -f -"

# Test unblocking  
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "pfctl -a kids_block -F rules"

# Check status
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "pfctl -a kids_block -s rules"
```

### Step 5: Restart and Test Home Assistant

**Restart Home Assistant:**
1. Go to **Settings > System > Restart**
2. Wait for restart to complete
3. Check logs for any errors

**Verify entities created:**
- `timer.kids_screen_time`
- `input_select.timer_duration` 
- `input_boolean.kids_devices_blocked`
- `sensor.kids_timer_status`

### Step 6: Configure Mobile App

**Install Home Assistant mobile app:**
1. Download from App Store (iOS) or Play Store (Android)
2. Log in with your Home Assistant credentials
3. Enable notifications when prompted

**Add dashboard to favorites:**
1. Open Home Assistant app
2. Navigate to the Kids Screen Time dashboard
3. Add to favorites for quick access

**Test notifications:**
1. Start a timer from the app
2. Verify you receive notification
3. Test notification actions (extend timer)

### Step 7: System Testing

**Test complete workflow:**

1. **Start Timer Test:**
   - Open Home Assistant mobile app
   - Navigate to Kids Screen Time dashboard
   - Select 15-minute duration
   - Tap "Start Timer"
   - Verify kids' devices have internet access
   - Check timer countdown is working

2. **Timer Expiration Test:**
   - Wait for timer to expire (or set very short timer)
   - Verify kids' devices lose internet access
   - Confirm local network access still works
   - Check notification received

3. **Manual Override Test:**
   - Toggle "Internet Access Blocked" switch
   - Verify immediate blocking/unblocking
   - Test emergency unblock script

4. **Device Testing:**
   From each child's device, test:
   - Internet websites (should be blocked when timer expires)
   - Local network resources (should always work)
   - Nintendo Switch online vs local multiplayer

### Step 8: Fine-tuning

**Adjust notification settings:**
- Customize notification messages
- Set up notification groups for multiple parents
- Configure notification actions

**Optimize dashboard:**
- Arrange cards for best mobile experience
- Add quick action buttons
- Customize icons and colors

**Set up monitoring:**
- Enable logging for troubleshooting
- Create history graphs
- Set up alerts for system issues

## Troubleshooting

### Common Issues

**SSH Connection Fails:**
- Check pfSense SSH is enabled
- Verify public key is correctly added
- Test network connectivity
- Check SSH port (default 22)

**Timer Starts But Devices Not Blocked:**
- Verify KID_DEVICES alias has correct IPs
- Check pfctl commands execute without errors
- Ensure devices use your DHCP server
- Test firewall commands manually

**Notifications Not Working:**
- Check mobile app is logged in
- Verify notification permissions enabled
- Test with simple notification first
- Check Home Assistant mobile integration

**Dashboard Not Loading:**
- Check YAML syntax in dashboard config
- Verify all entities exist
- Restart Home Assistant
- Check browser console for errors

### Getting Help

**Log Files to Check:**
- Home Assistant: Settings > System > Logs
- pfSense: Status > System Logs > Firewall
- Mobile App: Settings > Debugging

**Useful Commands:**
```bash
# Check Home Assistant logs
docker logs homeassistant

# Test SSH from Home Assistant
ssh -i /config/ssh_keys/pfsense_key admin@PFSENSE_IP "pfctl -s info"

# Check pfSense firewall state
pfctl -s rules | grep -i kid
```

## Security Notes

- SSH private key is stored securely in Home Assistant
- Commands execute with minimal required privileges
- Firewall rules are temporary (don't survive pfSense reboot)
- System can be manually overridden from pfSense interface
- All actions are logged for audit purposes

## Next Steps

Once the basic system is working:

1. **Add Warning System:** Implement 5-minute warnings before blocking
2. **Individual Device Control:** Separate timers for each child
3. **Scheduled Blocking:** Automatic bedtime/homework time blocking  
4. **Usage Statistics:** Track and report screen time usage
5. **Geofencing:** Location-based rule adjustments

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review pfSense and Home Assistant documentation
3. Test individual components (SSH, firewall commands, timers)
4. Check system logs for error messages

The system is designed to be robust and fail-safe - if something goes wrong, internet access will typically be restored automatically.