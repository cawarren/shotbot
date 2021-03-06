# shotbot
Script to help identify and mobilize political action related to gun violence.

The script currently:
- Fetches a list of yesterday's incidents relating to gun violence (incl. city/state and link to source), 
- Finds the geolocation of each of the incidents (lat/long), 
- Identifies which state and national legislators represent the area of the incident,
- Gets their contact info (email addresses for state representatives, also Facebook and Twitter info for national legislators), 
- Gets campaign contributions made to each representative (national only) from the 'Gun Rights' industry

Shotbot uses data provided by:
- Sunlight Labs (http://sunlightfoundation.com/api/)
- The Center for Responsive Politics' OpenSecrets.org (https://www.opensecrets.org)
- The Google Geocoding API (https://developers.google.com/maps/documentation/geocoding)

Based on an idea by S. Schaevitz.

## Usage
### Dependencies
Prerequisites to run the script:

    pip install beautifulsoup4
    pip install sunlight

Also, download and install the CRP API client library from VoteSmart:
https://github.com/votesmart/python-crpapi

### Configuration

You'll need to create a config.json file in the same directory as shotbot.py, 
with the following key/values:

     {
          "sunlight_api_key":"<your key here - get one from https://goo.gl/Mfp5qr>",
          "crp_api_key":"<your key here - get one from https://goo.gl/BnlL9q>",
          "google_api_key":"<your key here - get one from https://goo.gl/DsF2Qu>"
     } 

### Usage
Just run the script to see output in the terminal:

    python shotbot.py

