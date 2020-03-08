## Python Environment Management 
https://docs.python-guide.org/dev/virtualenvs/

## Install packages using the pip command:

$ pip install \<packagename\>

## To run: 
with config values in config file
$pipenv run python main.py --parameterfile parameters.json --logfile keyvaultcrawler.log
with config values in environment variables
$pipenv run python main.py --logfile keyvaultcrawler.log


## Refer: https://github.com/mattfeltonma/azure-keyvault-reporter/blob/master/key-vault-reporter.py