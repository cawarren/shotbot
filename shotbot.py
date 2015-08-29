
"""
Prerequisites to run the script:

pip install beautifulsoup4
pip install sunlight

Download and install https://github.com/votesmart/python-crpapi
"""

from crpapi import CRP, CRPApiError
from datetime import date
from bs4 import BeautifulSoup
from urllib2 import Request, urlopen, URLError

import json
import re
import sunlight

# The config variables (see importConfig)
config = {}

# Gun violence scraping URLs
GVA_ROOT_URL = 'http://www.gunviolencearchive.org'
GVA_PAGES_URL = 'http://www.gunviolencearchive.org/last-72-hours?page='

# Google Geocoding API
GEOCODING_ROOT_URL = 'https://maps.googleapis.com/maps/api/geocode/json?'
GOOGLE_API_KEY = ''	# Loaded in importConfig

# OpenSecrets API
CRP_API_ROOT_URL = "http://www.opensecrets.org/api/?method=CandIndByInd&output=json&"
CRP_INDUSTRY_CODE = 'Q13'


"""
getIncidents

Finds all gun violence incidents reported on gunviolencearchive.org from the day before,
adds them to the incidents list. 

Scrapes the GVA website for this info.
"""
def getIncidents():
  
  # The list we use to store incidents and relevant legislators
  incidents = []

  # Format yesterday's date to match the site we're scraping from
  yesterday = date.fromordinal(date.today().toordinal()-1)
  
  # Can't break loop on HTTP error response as the server never does, just
  # continues to return the last page when you go beyond it. Here we instead 
  # go through the first 10 pages, which should be more than enough for the 
  # day before.
  for page_counter in range (0,10):
    
    print "Now retrieving incident reports page " + `(page_counter + 1)` + "..."
    
    # Fetch the page and parse the response HTML with BeautifulSoup
    incidents_request = Request(GVA_PAGES_URL + `page_counter`)

    try:
      response = urlopen(incidents_request)
      results = response.read()
    except URLError, e:
      print "HTTP error (" + e + ") while getting incidents, moving on."
      
    parsed_results = BeautifulSoup(results, 'html.parser')

    # Find all incident report rows on the page and add info
    for row in parsed_results.find_all(class_=re.compile("(even|odd)")):
      
      # Ensure date on the page for the incident was yesterday
      if (row.contents[0].contents[0] == yesterday.strftime("%B %d, %Y")):
	
	# Parse row into relevant fields and add to the incidents list
	try:
	  
	  # Get the row's incident links first - if these are missing, 
	  # we should skip the row since this info may not be reliable.
	  incident_link = row.contents[6].contents[0].contents[0].contents[0].get('href')
	  source_link = row.contents[6].contents[0].contents[2].contents[0].get('href')
	  
	  # Create list to hold the incident info, will be added to the incidents list
	  row_result = [None]*8

	  row_result[0] = row.contents[0].contents[0]		# Date (e.g., August 21, 2015)
	  row_result[1] = row.contents[1].contents[0]		# State (e.g., Indiana, or District of Columbia)
	  row_result[2] = row.contents[2].contents[0]		# City or county (e.g., Grapeview or Jenison (Georgetown Township))
	  row_result[3] = row.contents[3].contents[0]		# Address (e.g,. 200 block of North Monroe Street, or 48th and Wellington, or Howard St)
	  row_result[4] = row.contents[4].contents[0]		# Number killed, int
	  row_result[5] = row.contents[5].contents[0]		# Number injured, int  -- Note, if 0 killed or injured was an attempt or found weapon
	  row_result[6] = GVA_ROOT_URL + incident_link		# Link to gunviolencearchive info on incident
	  row_result[7] = source_link				# Link to news report
	  
	  # Appending to incidents happens within the try-block to ensure we
	  # skip the row if links aren't found / we get an IndexError.
	  incidents.append(row_result)
	  
	except IndexError, e:
	  print "------------------------------------------------"
	  print "IndexError reading results row, skipping:"
	  print "------------------------------------------------"
	  print row
	  print "------------------------------------------------"

  # Return list of incidents
  return incidents

"""
getGeocodes

For each incident found by getIncidents, finds a reasonable matching lat/long.
The location info going in is pretty fuzzy, so these are often 'center of the
town' or 'corner of two streets' lat/long's.

Uses the Google Geocoding API.
"""
def getGeocodes(incidents):
  
  print "Finding geocodes..."
  
  # For each incident, we call the Google Geocoding API with relevant query
  for incident in incidents:
  
    address_string = incident[3] + ',+' + incident[2] + ',+' + incident[1]
    geocode_url = GEOCODING_ROOT_URL + 'address=' + address_string + '&key=' + GOOGLE_API_KEY
    geocode_request = Request(geocode_url.replace(" ", "+"))

    try:
      response = urlopen(geocode_request)
      results = response.read()
    except URLError, e:
      print "Failed to get geocode response, error: ", e
    
    # Parse and store results from API call
    parsed_geocoding = json.loads(results)
    
    try:
      # Put lat/long into a list
      geocode_set = [parsed_geocoding['results'][0]['geometry']['location']['lat'], 
		    parsed_geocoding['results'][0]['geometry']['location']['lng']]
      
      # Append lat/long info to the incident record
      incident.append(geocode_set)
    
    except (IndexError, KeyError):
      # Since we're not sure where this happened, set lat/long to -1.
      print "Couldn't parse lat/long from geocode:"
      print "  Address: " + address_string
      print "  Results: " + `parsed_geocoding`
      
      incident.append([-1,-1])
      
  return incidents


"""
getCongressPeople

For each incident found by getIncidents, takes the lat/long found by
getGeocodes and finds all relevant federal and state legislators for that
lat/long. Records any relevant contact info available.

Uses the Sunlight Foundation 'Congress' and 'OpenStates' APIs.
"""
def getCongressPeople(incidents):
  
  print "Finding relevant legislators..."
  
  for incident in incidents:
    
    # Only proceed if we know where this occurred
    if incident[0][0] == -1:
      pass
    else:
      incident_legislators = []
      incident_local_legislators = []
      
      # Find national and local legislators who are responsible for the incident's lat/long
      legislators = sunlight.congress.locate_legislators_by_lat_lon(incident[8][0], incident[8][1])
      local_legislators = sunlight.openstates.legislator_geo_search(incident[8][0], incident[8][1])
      
      # Append a list of relevant info about each national legislator to the incident
      for legislator in legislators:
	
	legislator_info = []
	
	legislator_info.append(resolve(legislator, 'title'))				# 0 - 'Sen' or 'Rep'
	legislator_info.append(resolve(legislator, 'first_name'))			# 1 - 'Patty'
	legislator_info.append(resolve(legislator, 'last_name'))			# 2 - 'Murray'
	legislator_info.append(resolve(legislator, 'nickname'))				# 3 - None or a string
	legislator_info.append(resolve(legislator, 'twitter_id'))			# 4 - 'SenatorCantwell'
	legislator_info.append(resolve(legislator, 'facebook_id'))			# 5 - None or '450819048314124'
	legislator_info.append(resolve(legislator, 'phone'))				# 6 - '202-224-2621'
	legislator_info.append(resolve(legislator, 'fax'))				# 7 - '202-224-0238'
	legislator_info.append(resolve(legislator, 'party'))				# 8 - 'D' or 'R' or (presumably) 'I'
	legislator_info.append(resolve(legislator, 'contact_form'))			# 9 - 'http://www.murray.senate.gov/.../contactme'
	legislator_info.append(resolve(legislator, 'birthday'))				# 10 - '1950-10-11'
	legislator_info.append(resolve(legislator, 'term_start'))			# 11 - '2011-01-05'
	
	# Get past 5yr campaign contributions from Gun Rights groups for the legislator
	contrib_sum = getContributions(resolve(legislator, 'crp_id'))
	legislator_info.append(contrib_sum)				# 12 - e.g., '1837971' Contributions from Gun Rights orgs, USD
	
	incident_legislators.append(legislator_info)
	
      # Append national legislators list to the incident
      incident.append(incident_legislators)
      
      # Append a list of relevant info about each state legislator to the incident
      for legislator in local_legislators:

	local_legislator_info = []

	try:
	  
	  local_legislator_info.append(resolve(legislator, 'party'))			# 0 - 'Republican'
	  local_legislator_info.append(resolve(legislator, 'first_name'))		# 1 - 'Patty B.'
	  local_legislator_info.append(resolve(legislator, 'last_name'))		# 2 - 'Murray'
	  local_legislator_info.append(resolve(legislator, 'email'))			# 3 - 'a@b.com' or None
	  local_legislator_info.append(resolve(legislator['offices'][0], 'phone'))	# 4 - '202-224-0238'
	  local_legislator_info.append(resolve(legislator['offices'][0], 'fax'))	# 5 - '202-224-0238'
	  
	except (IndexError, KeyError):
	  
	  # Sometimes there are no offices listed. Missing fields are handled by resolve().
	  pass
	
	incident_local_legislators.append(local_legislator_info)
      
    # Append local legislators list to the incident
    incident.append(incident_local_legislators)
    
  return incidents


"""
getContributions

Takes a legislator CRP ID (currently national legislators only) and fetches contributions made
from the 'Gun Rights' industry in the 2012 and 2014 election cycles from CRP.

Uses the OpenSecrets by CRP API.
"""
def getContributions(crp_id):
  
  # Set up parameters for API call to get funding info
  kw_2012 = {"cid": crp_id, "cycle": "2012", "ind": CRP_INDUSTRY_CODE}
  kw_2014 = {"cid": crp_id, "cycle": "2014", "ind": CRP_INDUSTRY_CODE}
  
  try:

    # Get the contributions and extract the total (for 2012)
    contrib_2012 = CRP.candIndByInd.get(**kw_2012)
    result_2012 = contrib_2012['total']
			
  except KeyError:
    
    # Not altogether clear what kind of result would cause this, but to be safe we set the contribs to 0
    result_2012 = 0
    
    print "KeyError: Couldn't get contributions for candidate with crp_id of " + crp_id 
    print "2012: " + `contrib_2012`
    
  except CRPApiError, ce:
    
    # The API is pretty RESTful, and returns a 404 if there were no contributions found in the time period
    # The client library helpfully throws an exception in this case. So we catch it and set the value to 0.
    result_2012 = 0

  try:
    
    # Same game, but for 2014 campaign cycle.
    contrib_2014 = CRP.candIndByInd.get(**kw_2014)
    result_2014 = contrib_2014['total']
			
  except KeyError:
    
    result_2014 = 0
    
    print "KeyError: Couldn't get contributions for candidate with crp_id of " + crp_id 
    print "2014: " + `contrib_2014`
    
  except CRPApiError, ce:
    
    result_2014 = 0
    
  return (int(result_2012) + int(result_2014))


# Helper function - safety against KeyErrors from inconsistent API info
def resolve(input_dict, *keys):
   for key in keys:
       try:
           output = input_dict[key]
       except (KeyError, IndexError):
           return None
   return output


# Helper function - if field value is None return ''
def noneToString(input_val):
  if input_val == None:
    return ''
  else:
    return input_val


# Helper function - pulls in config.json values
def importConfig():
    
  try:

    # Open the config.json file and read in the variables to config[]
    with open('config.json') as data_file:    
      config = json.load(data_file)
    
    sunlight.config.API_KEY = config['sunlight_api_key']
    CRP.apikey = config['crp_api_key']
    GOOGLE_API_KEY = config['google_api_key']
    
  except (IOError, KeyError):
    
    print ("\nIt looks like you're missing API keys - double-check that \n"
	   "you have a config.json file in the same directory as shotbot, \n"
	   "with the following key/values:\n")
    print """
 {
      "sunlight_api_key":"<your key here - get one from https://goo.gl/Mfp5qr>",
      "crp_api_key":"<your key here - get one from https://goo.gl/BnlL9q>",
      "google_api_key":"<your key here - get one from https://goo.gl/DsF2Qu>"
 } \n"""
    exit()


def main():
  
  # Set up API keys for client libs
  importConfig()

  # Do the actual work - get the incidents, map them, and get relevant legislators
  imported_incidents = getIncidents()
  geo_tagged_incidents = getGeocodes(imported_incidents)
  incidents_with_reps = getCongressPeople(geo_tagged_incidents)
  
  # Print what we've found (useful for testing, otherwise remove)
  for incident in incidents_with_reps:
    print incident[0] + ': ' + "Incident in " + incident[2] + ", " + incident[1]
    print "  " + incident[5] + " injured, " + incident[4] + " killed."
    print "  Location: " + incident[3]
    print "  Relevant legislators:"
    
    for legislator in incident[9]:
      print "    National: " + legislator[0] + ". " + legislator[1] + " " + legislator[2]
      print "      Twitter: " + noneToString(legislator[4])
      if (legislator[12] != 0):
	print "      Has campaign contributions from Gun Rights industry: $" + `legislator[12]`
    
    for local_legislator in incident[10]:
      print "    State: " + local_legislator[1] + " " + local_legislator[2] + " (Email: " + noneToString(local_legislator[3]) + ")"
    
    print '\n'


if __name__ == "__main__":
    main()
