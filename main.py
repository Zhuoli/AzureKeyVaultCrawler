import datetime
import logging
import requests
import sys
import os
import json
import hmac
import base64
import hashlib
import msal

from datetime import datetime, timezone
from argparse import ArgumentParser
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from tabulate import tabulate
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Reusable function to create a logging mechanism
def create_logger(logfile=None):
        
    # Create a logging handler that will write to stdout and optionally to a log file
    stdout_handler = logging.StreamHandler(sys.stdout)
    try:
        if logfile != None:
            file_handler = logging.FileHandler(filename=logfile)
            handlers = [file_handler, stdout_handler]
        else:
            handlers = [stdout_handler]
    except Exception as e:
        handlers = [stdout_handler]
        print("Log file could not be created. Error: {}".format(e))

    # Configure logging mechanism
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers = handlers
    )

# Get access token using client credentials flow
def get_access_token(tenantname,scopes,client_id, client_secret):
    logging.info("Attempting to obtain an access token...")
    result = None
    app = msal.ConfidentialClientApplication(
        client_id = client_id,
        client_credential = client_secret,
        authority='https://login.microsoftonline.com/' + tenantname
    )
    result = app.acquire_token_for_client(scopes=scopes)

    if "access_token" in result:
        logging.info("Access token successfully acquired")
        return result['access_token']
    else:
        logging.error("Unable to obtain access token")
        logging.error(f"Error was: {result['error']}")
        logging.error(f"Error description was: {result['error_description']}")
        logging.error(f"Error correlation_id was: {result['correlation_id']}")
        raise Exception('Failed to obtain access token')

# Convert the offset to a readable timestamp
def convert_time(utc_offset):
    utctimestamp = datetime.fromtimestamp(utc_offset, timezone.utc)
    return utctimestamp

# Query Azure REST API
def rest_api_request(url,token,query_params=None):

    try:
        
        # Create authorization header
        headers = {'Content-Type':'application/json', \
            'Authorization':'Bearer {0}'.format(token)}

        # Issue request to Azure API
        logging.info(f"Issuing request to {url}")
        response = requests.get(
            headers=headers,
            url=url,
            params=query_params
        )

        # Validate and process response
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            logging.error('Error encountered querying Azure API')
            logging.error(f"Error code was: {(json.loads(response.text))['error']['code']}")
            logging.error(f"Error message was: {(json.loads(response.text))['error']['message']}")
            raise Exception

    except Exception:
        return json.loads(response.text)

# Function which builts signature to sign requests to Azure Monitor API
def build_signature(customer_id, shared_key, date, content_length, method, content_type, resource):
    x_headers = 'x-ms-date:' + date
    string_to_hash = method + "\n" + str(content_length) + "\n" + content_type + "\n" + x_headers + "\n" + resource
    bytes_to_hash = bytes(string_to_hash, encoding="utf-8")  
    decoded_key = base64.b64decode(shared_key)
    encoded_hash = base64.b64encode(
        hmac.new(decoded_key, bytes_to_hash, digestmod=hashlib.sha256).digest()).decode()
    authorization = "SharedKey {}:{}".format(customer_id,encoded_hash)
    return authorization

# Function which posts data to Azure Monitor API  
# CustomerID : The unique identifier for the Log Analytics workspace.
def post_data_to_azure_log(customer_id, shared_key, body, log_type):
    method = 'POST'
    content_type = 'application/json'
    resource = '/api/logs'
    rfc1123date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    content_length = len(body)
    signature = build_signature(customer_id, shared_key, rfc1123date, content_length, method, content_type, resource)
    uri = 'https://' + customer_id + '.ods.opinsights.azure.com' + resource + '?api-version=2016-04-01'

    headers = {
        'content-type': content_type,
        'Authorization': signature,
        'Log-Type': log_type,
        'x-ms-date': rfc1123date
    }

    response = requests.post(uri,data=body, headers=headers)
    if (response.status_code >= 200 and response.status_code <= 299):
        logging.info("Accepted")
    else:
        logging.error("Data was not posted to API.  Response code: {}".format(response.status_code))

def post_data_to_azure_automation(uri, body):
    method = 'POST'
    content_type = 'application/json'
    headers = {
        'content-type': content_type,
        'message': 'ZhuoliKeyVaultMonitorScript',
    }

    response = requests.post(uri,data=body, headers=headers)
    if (response.status_code >= 200 and response.status_code <= 299):
        logging.info("Accepted")
    else:
        logging.error("Data was not posted to API.  Response code: {}".format(response.status_code))

#def convertTableToHtmlTable(tablebody):
    #

def post_data_to_email(SENDGRID_API_KEY, from_email, to_emails, tablebody):
    logging.info(f"Send email to:  {to_emails}")
    logging.info(f"send email from:  {from_email}")

    html = """
    <html><body><p>Hello, Friend.</p>
    <p>Here is your KeyVault report:</p>
    {table}
    <p>Regards,</p>
    <p>Microsoft ARO team</p>
    </body></html>
    """
    html = html.format(table=tabulate(tablebody, headers="firstrow", tablefmt="html"))

    message = Mail(
        from_email=from_email,
        to_emails=to_emails,
        subject='ARO KeyVault Monitor Report',
        html_content=html
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logging.info(response.status_code)
        logging.info(response.body)
        logging.info(response.headers)
    except Exception as e:
        logging.error(e)
        logging.error(e.message)

def shrink_table(tableheader, tablebody):
    headers = tableheader.split(',')
    result=[]
    for row in tablebody:
        newrow = []
        for header in headers:
            newrow.append(row[header])
        result.append(newrow)
    result.sort(key=lambda x: x[len(headers)-1])
    result.insert(0,headers)
    return result

def load_config():
    config={}
    config['tenantname'] = os.getenv('TENANT_NAME')
    config['clientid'] = os.getenv('AZURE_CLIENT_ID')
    config['clientsecret'] = os.getenv('AZURE_CLIENT_SECRET')
    config['workspaceid'] = os.getenv('workspaceid')
    config['workspacekey'] = os.getenv('workspacekey')
    config['logname'] = os.getenv('logname')
    config['subscription_ids'] = (os.getenv('SUBSCRIPTION_IDS') or "").split(',')
    config['sendgrid_key'] = os.getenv('SENDGRID_KEY')
    config['emailfrom'] = os.getenv('EMAIL_FROM')
    config['emailto'] = os.getenv('EMAIL_TO')
       
    return config
def main():

    try:

        # Setup variable for API versions of Azure Resource Management API and Key Vault API
        mgmt_api_version = '2019-08-01'
        kv_api_version = '7.0'

        # Setup other variables used throughout solution
        data_types = [
            'secrets'
        ]
        vault_list = []
        key_vault_records = []
        
        # Process arguments
        parser = ArgumentParser()
        parser.add_argument('--parameterfile', type=str, help='JSON file with parameters')
        parser.add_argument('--logfile', type=str, help='Specify an optional log file')
        args = parser.parse_args()

        # Create logging mechanism
        create_logger(args.logfile)

        config = None;
        # Retrieve parameters from parameter file
        if (args.parameterfile is None):
            config = load_config()
        else:
            with open(args.parameterfile) as json_data:
                config = json.load(json_data)
        

        # Retrieve access token for Azure Resource Management API
        logging.info('Requesting acess token for Azure Resource Management API...')
        mgmt_api_token = get_access_token(
            tenantname = config['tenantname'],
            scopes = [
                'https://management.azure.com//.default'
            ],
            client_id = config['clientid'],
            client_secret = config['clientsecret']
        )

        # Retrieve access token for Key Vault API
        logging.info('Requesting acess token for Key Vault API...')
        keyvault_api_token = get_access_token(
            tenantname = config['tenantname'],
            scopes = [
                'https://vault.azure.net/.default'        
            ],
            client_id = config['clientid'],
            client_secret = config['clientsecret']
        )

        # Retrieve a list of vaults in a subscription
        for subscription_id in config['subscription_ids']:

            query_params = {
                'api-version': mgmt_api_version,
                '$filter': "resourceType eq 'Microsoft.KeyVault/vaults'"
            }

            vaults_response = rest_api_request(
                url = f"https://management.azure.com/subscriptions/{subscription_id}/resources",
                token = mgmt_api_token,
                query_params = query_params
            )

            if 'error' not in vaults_response:
                for vault in vaults_response['value']:

                    vault_item = {
                        'subscription_id':subscription_id,
                        'key_vault_id':vault['id'],
                        'key_vault_name':vault['name'],
                        'location':vault['location']
                    }
                    vault_list.append(vault_item)

                    while 'nextLink' in vaults_response:
                        logging.info('Paged results returned...')
                        vaults_response = rest_api_request(
                            url = vaults_response['nextLink'],
                            token = mgmt_api_token
                        )

                        for vault in vaults_response['value']:

                            vault_item = {
                                'subscription_id':subscription_id,
                                'key_vault_id':vault['id'],
                                'key_vault_name':vault['name'],
                                'location':vault['location']
                            }
                            vault_list.append(vault_item)

        # Iterate through keys and secrets in each Key Vault to determine age
        for vault in vault_list:
            
            # Setup the request to query Key Vault API 
            query_params = {
                'api-version': kv_api_version
            }

            # Iterate through both keys and secrets
            for data_type in data_types:

                key_vault_response =  rest_api_request(
                    url = f"https://{vault['key_vault_name']}.vault.azure.net/{data_type}",
                    token = keyvault_api_token,
                    query_params = query_params
                )
                
                # Create a record for each key or secret
                if 'error' not in key_vault_response:
                    for key_vault_data in key_vault_response['value']:
                        key_vault_record = {
                                'subscription':vault['subscription_id'],
                                'key_vault':vault['key_vault_name'],
                                'created':(str(convert_time(key_vault_data['attributes']['created']))),
                                'updated':(str(convert_time(key_vault_data['attributes']['updated']))),
                                'enabled':key_vault_data['attributes']['enabled'],
                                'age':((datetime.now(timezone.utc) - (convert_time(key_vault_data['attributes']['created']))).days)
                        }

                        # Logic to handle different attributes returned by key vs secret
                        if data_type == 'keys':
                            key_vault_record['data_id'] = key_vault_data['kid']
                            key_vault_record['data_type'] = 'key'
                        else:
                            key_vault_record['data_id'] = key_vault_data['id']
                            key_vault_record['data_type'] = 'secret'

                        # If expiration is present record the date and time
                        if 'exp' in key_vault_data['attributes']:
                            key_vault_record['expires'] = (str(convert_time(key_vault_data['attributes']['exp'])))
                        else:
                            key_vault_record['expires'] = None

                        key_vault_record['name']=key_vault_record['data_id'].split('/')[-1]
                        # Append the record to the list
                        key_vault_records.append(key_vault_record)

        # Deliver data to Azure Monitor API
        json_data = json.dumps(key_vault_records)
        tableheaders='key_vault,name,expires'
        tablebody = shrink_table(tableheaders, key_vault_records)
        logging.info(f"Crawlled keyvaults: {vault_list}")
        # post_data_to_azure_log(customer_id = config['workspaceid'],shared_key = config['workspacekey'],body = json_data,log_type = config['logname'])
        # post_data_to_azure_automation(config['webhookurl'], json_data)
        post_data_to_email(config['sendgrid_key'], config['emailfrom'], config['emailto'], tablebody)
        # print("Done. Sent to Azure Monitor with name" + config['logname'])
    except Exception:
        logging.error('Execution error',exc_info=True)

if __name__ == "__main__":
    main()