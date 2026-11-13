# TOMMY (Home Assistant Integration)

This is the Home Assistant integration for TOMMY, allowing you to integrate your TOMMY zones with Home Assistant.

## Getting Started

The Home Assistant Integration Guide covers everything you need to know about setting up TOMMY in Home Assistant, including installation, configuration, and troubleshooting tips.

[Get started: Home Assistant Integration Guide](https://www.tommysense.com/docs/integration/homeassistant)

[Learn more: Full Documentation](https://www.tommysense.com/docs)

## Installation

The TOMMY integration installs from the Marketplace built into Home Assistant 2026.11 and newer.

[![Open your Home Assistant instance and show the TOMMY repository in the Marketplace.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tommy-sense&repository=homeassistant-integration&category=integration)

1. In Home Assistant, go to Settings → Marketplace
2. Click **Add from link** in the upper right
3. Enter `tommy-sense/homeassistant-integration` and click **Add**. Connect GitHub if Home Assistant asks you to
4. Open **TOMMY**, click **Install** and confirm the version with **Install**
5. If Home Assistant asks for a restart under Settings → System → Repairs, restart it
6. Configure the TOMMY integration (see Configuration below)

New versions show up under Settings → Updates. Install them there and restart Home Assistant. From TOMMY 8.0.0, the TOMMY dashboard tells you when the integration needs an update.

## Configuration

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "TOMMY"
4. Fill out the details when prompted:
   - Enter the IP address of your Home Assistant instance (for App) or the Docker container running TOMMY (for Docker)
   - Enter the MQTT Port assigned in your TOMMY configuration (App configuration) or environment variables (Docker installation) (default: 1886)

## Zones

You don't need to configure anything for zones to show up. Home Assistant will automatically stay in sync with zones in the dashboard when adding, removing, or renaming zones. For each zone, a motion sensor entity is exposed in Home Assistant.
