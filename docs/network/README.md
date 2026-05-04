# Parental Control Timer System

A comprehensive Home Assistant and pfSense integration that allows parents to set timers for children's internet access, controllable from mobile devices.

## 🎯 Features

- **Timer-based Internet Control**: Set 15min, 30min, 1hr, or 2hr timers for internet access
- **Mobile App Control**: Start/stop timers directly from Home Assistant mobile app
- **Smart Blocking**: Blocks internet access while preserving local network connectivity
- **Emergency Override**: Quick unblock functionality for emergencies
- **Notification System**: Get notified when timers start, expire, or are extended
- **Device Support**: Works with Android phones, iPhones, iPads, Nintendo Switch, and any WiFi/Ethernet connected device
- **Robust Architecture**: Fail-safe design with automatic state synchronization

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Mobile App     │───▶│  Home Assistant  │───▶│     pfSense     │
│  (iOS/Android)  │    │      (VM)        │    │      (VM)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  Timer & Logic   │    │ Firewall Rules  │
                       │   Automations    │    │  (KID_DEVICES)  │
                       └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │ Children's      │
                                              │ Devices         │
                                              │ • Android Phone │
                                              │ • iPhone        │
                                              │ • iPad          │
                                              │ • Nintendo SW   │
                                              └─────────────────┘
```

## 📋 Prerequisites

- Home Assistant running in VM on Proxmox
- pfSense running in VM on Proxmox
- Existing `KID_DEVICES` alias in pfSense with children's device IPs
- Administrative access to both systems
- Home Assistant mobile app installed

## 🚀 Quick Start

1. **Clone or download this repository**
2. **Follow the [Installation Guide](scripts/installation-guide.md)**
3. **Configure your device IPs in pfSense KID_DEVICES alias**
4. **Test the system with a short timer**

## 📁 Project Structure

```
NetworkScripts/
├── docs/
│   └── parental-control-timer-plan.md    # Detailed architecture plan
├── scripts/
│   ├── home-assistant/
│   │   ├── configuration.yaml            # HA configuration additions
│   │   ├── automations.yaml             # Timer automations
│   │   ├── scripts.yaml                 # Helper scripts
│   │   └── dashboard.yaml               # Mobile-friendly dashboard
│   ├── pfsense/
│   │   ├── setup-ssh-access.sh          # SSH setup automation
│   │   └── firewall-commands.md         # pfSense command reference
│   └── installation-guide.md            # Step-by-step setup guide
└── README.md                            # This file
```

## 🔧 How It Works

### Timer Flow
1. **Start Timer**: Parent selects duration and starts timer from mobile app
2. **Internet Enabled**: Children's devices get full internet access
3. **Timer Expires**: Firewall rules automatically block internet access
4. **Local Access Preserved**: Devices can still access local network resources

### Blocking Method
- **Blocks**: Outbound internet traffic from children's devices
- **Preserves**: Local network access (file shares, printers, local multiplayer)
- **Method**: pfSense firewall rules targeting `KID_DEVICES` alias
- **Control**: SSH commands from Home Assistant to pfSense

### Mobile Integration
- Native Home Assistant mobile app integration
- Push notifications for timer events
- Quick action buttons for common durations
- Emergency override functionality

## 📱 Mobile App Features

### Dashboard Controls
- Timer duration selector (15min, 30min, 1hr, 2hr)
- Start/Stop timer buttons
- Current status display
- Manual block/unblock toggle
- Quick timer buttons

### Notifications
- Timer started confirmation
- Timer expiration alerts
- Extension options via notification actions
- Emergency override confirmations

## 🔒 Security Features

- **SSH Key Authentication**: Secure communication between systems
- **Minimal Privileges**: Commands execute with least required access
- **Audit Trail**: All actions logged for monitoring
- **Fail-Safe Design**: System defaults to allowing access if errors occur
- **Manual Override**: Can be overridden from pfSense interface

## 🛠️ Configuration

### pfSense Setup
- Create `KID_DEVICES` alias with children's device IPs
- Enable SSH access for Home Assistant
- Configure firewall logging (optional)

### Home Assistant Setup
- Add configuration sections to existing files
- Install mobile app and enable notifications
- Create dashboard for easy access
- Test SSH connectivity to pfSense

### Device Management
- Use DHCP reservations for consistent IP addresses
- Document device MAC addresses
- Test blocking effectiveness per device

## 📊 Monitoring & Troubleshooting

### Built-in Monitoring
- Timer status sensor
- Last action timestamp
- Firewall state synchronization
- Automatic health checks every 5 minutes

### Troubleshooting Tools
- SSH connection test script
- Firewall command reference
- Detailed logging configuration
- Step-by-step diagnostic guide

### Common Issues
- SSH connectivity problems
- Firewall rule conflicts
- Device IP changes
- Timer synchronization issues

## 🔮 Future Enhancements

### Planned Features
- **5-minute warning system** before blocking
- **Individual device timers** for each child
- **Scheduled automatic blocking** (bedtime, homework time)
- **Usage statistics and reporting**
- **Geofencing integration**

### Advanced Options
- **Reward system integration**
- **School hours automatic blocking**
- **Multiple user profiles**
- **API integration with other systems**

## 📖 Documentation

- **[Architecture Plan](docs/parental-control-timer-plan.md)**: Detailed system design
- **[Installation Guide](scripts/installation-guide.md)**: Step-by-step setup
- **[pfSense Commands](scripts/pfsense/firewall-commands.md)**: Firewall command reference
- **[SSH Setup](scripts/pfsense/setup-ssh-access.sh)**: Automated SSH configuration

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome:

1. Test the system in your environment
2. Report issues or edge cases
3. Suggest feature improvements
4. Share configuration optimizations

## ⚠️ Disclaimer

This system is designed for parental control purposes. It should be used responsibly and in accordance with your family's needs and local laws. The system is provided as-is without warranty.

## 📄 License

This project is provided under the MIT License. See individual files for specific licensing information.

---

**Created for**: Home network parental control  
**Tested with**: Home Assistant 2024.x, pfSense 2.7.x  
**Platform**: Proxmox VMs on Nipogi server  
**Language**: English/French documentation available