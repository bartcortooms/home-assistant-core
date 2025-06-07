# Viessmann ViCare CLI Sensor Lister

## Purpose

This command-line interface (CLI) tool, `vicare_cli.py`, connects to the Viessmann ViCare API to retrieve a list of all available sensors and their current values for your Viessmann heating system. It is based on the `PyViCare` library.

## Requirements

*   Python 3.x
*   Dependencies listed in `vicare_cli_requirements.txt` (primarily `PyViCare`).

## Installation & Setup

1.  **Clone the repository (if you haven't already).**
    ```bash
    # git clone ... (or if you're already in it)
    ```
2.  **Install dependencies:**
    It's recommended to use a Python virtual environment.
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r vicare_cli_requirements.txt
    ```

## Configuration & Credentials

The CLI tool requires your Viessmann ViCare credentials, which must be provided via command-line arguments:

*   `--username YOUR_USERNAME`: Your ViCare account username (usually your email).
*   `--password YOUR_PASSWORD`: Your ViCare account password.
*   `--client-id YOUR_CLIENT_ID`: The Client ID for the Viessmann API. You may need to obtain this from Viessmann developer resources or use a known one if available from other integrations.

### Optional Arguments:

*   `--heating-type TYPE`: Specifies the type of your heating system.
    *   Default: `auto`
    *   Choices: `auto`, `gas`, `oil`, `pellets`, `heatpump`, `fuelcell`, `hybrid`.
    *   `PyViCare` uses this to interact with the device correctly. `auto` is usually sufficient.
*   `--token-cache-path PATH`: Path to store the API token.
    *   Default: `vicare_token.save` (in the current directory).
    *   The script will save API tokens here after the first successful login. Subsequent runs will use the cached token, avoiding the need to re-enter credentials until the token expires.

## Usage Example

```bash
python vicare_cli.py --username "your_email@example.com" --password "yourSecretPassword" --client-id "yourApiClientId"
```

To specify a heating type:
```bash
python vicare_cli.py --username "..." --password "..." --client-id "..." --heating-type gas
```

To specify a token cache path:
```bash
python vicare_cli.py --username "..." --password "..." --client-id "..." --token-cache-path "/tmp/vicare_token.json"
```

## Output

The script will output a JSON object to standard output containing all discovered sensors and their current values. Each sensor key is prefixed to indicate its source (e.g., `global_`, `circuit_0_`, `burner_0_`).

Example (partial output):
```json
{
    "global_outside_temperature": {
        "value": 10.5,
        "unit": "°C"
    },
    "circuit_0_supply_temperature": {
        "value": 35.0,
        "unit": "°C"
    }
    // ... more sensors
}
```
Error messages and informational logs are printed to standard error.
