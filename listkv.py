from azure.keyvault import KeyVaultClient
from azure.common.credentials import ServicePrincipalCredentials
from azure.keyvault.secrets import SecretClient
import os

credentials = ServicePrincipalCredentials(
    client_id = os.getenv('AZURE_CLIENT_ID'),
    secret = os.getenv('AZURE_CLIENT_SECRET'),
    tenant = os.environ.get('AZURE_CLIENT_TENANT')
)

client = KeyVaultClient(credentials)

VAULT_URL="https://zhuolikeyvaultmonitor.vault.azure.net/"
# VAULT_URL must be in the format 'https://<vaultname>.vault.azure.net'
# KEY_VERSION is required, and can be obtained with the KeyVaultClient.get_key_versions(self, vault_url, key_name) API
secretBundle = client.get_secret(VAULT_URL, "ZhuoliSecretExpire", "930d7bdf9ff448d4b61d2974c2d2940c")
print(secretBundle.attributes)

# secrets = secret_client.list_properties_of_secrets()
# secret_client = SecretClient(vault_url, credentials)
# for secret in secrets:
#     # the list doesn't include values or versions of the secrets
#     print(secret.id)
#     print(secret.name)
#     print(secret.enabled)