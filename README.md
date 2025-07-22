# Atomberg

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

*Integration for **[Atomberg smart fans](https://atomberg.com/atomberg-ceiling-fans/smart-fans)***

## Tested on
- **[Atomberg Renesa+ Ceiling Fan](https://atomberg.com/atomberg-renesa-smart-iot-enabled-ceiling-fans-with-bldc-motor-and-remote)**
- **[Atomberg Aris Ceiling Fan](https://atomberg.com/aris-ceiling-fan)**
- **[Atomberg Erica Ceiling Fan](https://atomberg.com/erica-ceiling-fan)**

## Installation

### Method 1: Using HACS

1. Open your Home Assistant UI.
2. Go to "HACS" (Home Assistant Community Store).
3. Search for "Atomberg" in the search bar.
4. You should see the Atomberg integration listed.
5. Click "Install" and follow any prompts to complete the installation.

### Method 2: Manual Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `atomberg`.
4. Download _all_ the files from the `custom_components/atomberg/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant.

## Configuration

### Step 1: Generate API Key and Refresh Token
1. Go to [Atomberg Developer Portal](https://developer.atomberg-iot.com/#overview).
2. Follow the instructions to generate your `api_key` and `refresh_token`.

### Step 2: Add Atomberg Integration to Home Assistant
1. Open your Home Assistant UI.
2. Navigate to "Configuration" -> "Integrations".
3. Click the "+" icon to add a new integration.
4. Search for "Atomberg" in the integration search bar and select it.

### Step 3: Enter API Key and Refresh Token
1. Enter your `api_key` and `refresh_token` in the appropriate fields.
2. Submit the form.

## Compatibility and Requirements

- Please note that this integration is designed for the latest series of Atomberg fans and may not work with older models.
- The integration relies on cloud APIs for initialization.
- This integration uses UDP port `5625` for updating the fan state locally, make sure that port is not in use by any other application and that it is not blocked by any firewall.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

## Credits

- Code template was mainly taken from [@Ludeeus](https://github.com/ludeeus)'s [integration_blueprint][integration_blueprint] template
- Atomberg IoT Team


[integration_blueprint]: https://github.com/ludeeus/integration_blueprint
[commits-shield]: https://img.shields.io/github/commit-activity/y/dasshubham762/atomberg-integration.svg?style=for-the-badge
[commits]: https://github.com/dasshubham762/atomberg-integration/commits/main
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/dasshubham762/atomberg-integration.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40dasshubham762-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/dasshubham762/atomberg-integration.svg?style=for-the-badge
[releases]: https://github.com/dasshubham762/atomberg-integration/releases
