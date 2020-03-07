from azure.keyvault import KeyVaultClient
from azure.common.credentials import ServicePrincipalCredentials
import os

credentials = ServicePrincipalCredentials(
    client_id = os.getenv('AZURE_CLIENT_ID')
    secret = os.getenv('AZURE_CLIENT_SECRET')
    tenant = os.environ.get('AZURE_CLIENT_TENANT')
)

client = KeyVaultClient(credentials)

# VAULT_URL must be in the format 'https://<vaultname>.vault.azure.net'
# KEY_VERSION is required, and can be obtained with the KeyVaultClient.get_key_versions(self, vault_url, key_name) API
VAULT_URL="osa-global"
KEY_NAME="?sd"
KEY_VERSION=""
key_bundle = client.get_key(VAULT_URL, KEY_NAME, KEY_VERSION)
key = key_bundle.key