[log_analytics://<name>]
resource_group = 
workspace_id = 
subscription_id = 
tenant_id = 
application_id = 
application_key = 
log_analytics_query = 
start_date = Start date must be in the format of dd/mm/yyyy hh:mm:ss
event_delay_lag_time = Number in minutes to look into the past.  The events flow into log analytics in 5 minute intervals, making it impossible for real time.  We default to 15 minutes lag.