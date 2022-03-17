# encoding = utf-8

import sys
import datetime
import json
import requests
from splunklib.modularinput import *

API_URL = "https://api.loganalytics.io"

def authenticate(helper, tenant_id, application_id, application_key):
	login_url = "https://login.microsoftonline.com/{}/oauth2/token".format(tenant_id)

	payload = {
		"grant_type": "client_credentials",
		"client_id": application_id,
		"client_secret": application_key,
		"resource": API_URL
	}
	headers = {"content-type": "application/x-www-form-urlencoded"}

	response = requests.post(login_url, data=payload, headers=headers)

	try:
		response.raise_for_status()
		resp = response.json()
		acess_token = resp["access_token"]
	except Exception as err:
		helper.log_error("Could not retrive access token: {}".format(err))
		sys.exit(1)

	return acess_token


def validate_input(helper, definition):
	inputs=helper.get_input_stanza()
	for input_name, input_item in inputs.items():
		start_date = str(input_item["start_date"])
		try:
			valid_date = datetime.datetime.strptime(start_date, '%d/%m/%Y %H:%M:%S')
		except ValueError:
			helper.log_error("Start date must be in the format of dd/mm/yyyy hh:mm:ss")
	pass

def collect_events(helper, ew):

		# Get the values, cast them as floats
		input_name=helper.get_input_stanza_names()
		resource_group = str(helper.get_arg('resource_group'))
		workspace = str(helper.get_arg('workspace_id'))
		query = str(helper.get_arg('log_analytics_query'))
		subscription_id = str(helper.get_arg('subscription_id'))
		tenant_id = str(helper.get_arg('tenant_id'))
		application_id = str(helper.get_arg('application_id'))
		application_key = helper.get_arg('application_key')
		event_lag = int(float(helper.get_arg('event_delay_lag_time')))

		# Date and delta
		if helper.get_check_point(input_name):
			start_datetime = datetime.datetime.strptime(helper.get_check_point(input_name),'%d/%m/%Y %H:%M:%S')
		else:
			start_datetime = datetime.datetime.strptime(str(helper.get_arg('start_date')),'%d/%m/%Y %H:%M:%S')
		now = datetime.datetime.utcnow() - datetime.timedelta(minutes=event_lag)
		now_dt = now.replace(microsecond=0)

		# Get access token
		access_token = authenticate(helper, tenant_id, application_id, application_key)

		# Add token to header
		headers = {
			"Authorization": 'Bearer ' + access_token,
			"Content-Type":'application/json'
		}

		# URLs for retrieving data
		uri = "{}/v1/workspaces/{}/query".format(API_URL, workspace)

		# Build search parameters from query details
		search_params = {
			"query": query,
			"timespan": start_datetime.strftime('%Y-%m-%dT%H:%M:%S') + '/' + now_dt.strftime('%Y-%m-%dT%H:%M:%S')
		}

		# Send post request
		response = requests.post(uri, json=search_params, headers=headers)
		response.raise_for_status()

		# Response of 200 if successful
		if response.status_code == 200:
			# If debug, log event
			helper.log_debug('OMSInputName="' + str(input_name) + '" status="' + str(response.status_code) + '" step="Post Query" search_params="' + str(search_params) + "'")
			# Parse the response to get the ID and status
			data = response.json()
		else:
			# Request failed
			helper.log_error('OMSInputName="' + str(input_name) + '" status="' + str(response.status_code) + '" step="Post Query" response="' + str(response.text) + '"')
			
		#Building proper json format from original request
		#First loop checks how many events returned is in response
		
		rows = []
		for row in data["tables"][0]["rows"]:
			row_data = {}
			for i, entry in enumerate(row):
				col_name = data["tables"][0]["columns"][i]["name"]
				col_value = entry
				row_data[col_name] = col_value
			rows.append(row_data)

		for row in rows:
			event = helper.new_event(
				source=helper.get_input_type(), 
				index=helper.get_output_index(),
				sourcetype="loganalytics",
				data=json.dumps(row)
			)
			ew.write_event(event)

		#Delta
		state = now_dt.strftime("%d/%m/%Y %H:%M:%S")
		helper.save_check_point(input_name, state)    
