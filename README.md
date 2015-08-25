# shotbot
Script to help identify and mobilize political action related to gun violence.

The script currently:
- Fetch a list of yesterday's incidents relating to gun violence (incl. city/state and link to source), 
- Find the geolocation of each of the incidents (lat/long), 
- Identify which state and national legislators represent the area of the incident,
- Get their contact info (email addresses for state representatives, plus Facebook and Twitter info for national legislators), 
- Get campaign contributions made to each representative (national only) from the 'Gun Rights' industry

Shotbot uses data provided by:
- Sunlight Labs (http://sunlightfoundation.com/api/)
- The Center for Responsive Politics' OpenSecrets.org (https://www.opensecrets.org)
- The Google Geocoding API (https://developers.google.com/maps/documentation/geocoding)
