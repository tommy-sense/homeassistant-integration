# TOMMY (Home Assistant Integration)

This is the Home Assistant integration for TOMMY, allowing you to integrate your TOMMY zones with Home Assistant.

> **⚠️ Pro Edition Required**
> 
> This integration will only sync with **TOMMY Pro Edition** instances. Community Edition users can use the [Matter integration](https://www.tommysense.com/docs/integration/matter) instead.

## Getting Started

The Home Assistant Integration Guide covers everything you need to know about setting up TOMMY in Home Assistant, including installation, configuration, and troubleshooting tips.

[Get started: Home Assistant Integration Guide](https://www.tommysense.com/docs/integration/homeassistant)

[Learn more: Full Documentation](https://www.tommysense.com/docs)

## Installation

### Manual Installation

1. [Download the latest release](https://github.com/tommy-sense/homeassistant-integration/releases/latest).
2. Unpack the release and copy the `custom_components/tommy` directory into the `config/custom_components` directory of your Home Assistant installation.
   - The directory structure should be `config/custom_components/tommy`
3. Restart Home Assistant.
4. Configure the TOMMY integration (see Configuration below).

### Installation using Home Assistant Community Store (HACS)

Coming soon

## Configuration

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "TOMMY"
4. Fill out the details when prompted:
   - Enter the IP address of your Home Assistant instance (for Add-on) or the Docker container running TOMMY (for Docker)
   - Enter the MQTT Port assigned in your TOMMY configuration (Add-on configuration) or environment variables (Docker installation) (default: 1886)

## Zones

You don't need to configure anything for zones to show up. Home Assistant will automatically stay in sync with zones in the dashboard when adding, removing, or renaming zones. For each zone, a motion sensor entity is exposed in Home Assistant.