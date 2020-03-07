import requests
from azure.keyvault import KeyVaultClient
from azure.common.credentials import ServicePrincipalCredentials
from azure.keyvault.secrets import SecretClient
import os

response = requests.get('https://httpbin.org/ip')

def getIP():
    print('Your IP is {0}'.format(response.json()['origin']))

def retrieveSingleKeyVaultAttributes(vault_url, resourceName, version, credentials):
    client = KeyVaultClient(credentials)
    secretBundle = client.get_secret(vault_url, resourceName, version)
    return secretBundle.attributes

def main():
    credentials = ServicePrincipalCredentials(
        client_id = os.getenv('AZURE_CLIENT_ID'),
        secret = os.getenv('AZURE_CLIENT_SECRET'),
        tenant = os.environ.get('AZURE_CLIENT_TENANT')
    )
    client = KeyVaultClient(credentials)
    VAULT_URL="https://zhuolikeyvaultmonitor.vault.azure.net/"
    resourceName="ZhuoliSecretExpire"
    version="930d7bdf9ff448d4b61d2974c2d2940c"
    # VAULT_URL must be in the format 'https://<vaultname>.vault.azure.net'
    # KEY_VERSION is required, and can be obtained with the KeyVaultClient.get_key_versions(self, vault_url, key_name) API
    print(retrieveSingleKeyVaultAttributes(VAULT_URL,version, client)
    

if __name__ == "__main__":
    # execute only if run as a script
    main()