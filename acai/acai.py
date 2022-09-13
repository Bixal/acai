#!/usr/bin/python3

# Copyright 2022 John Franklin <john.franklin@bixal.com>
# Copyright 2022 Bixal Solutions, inc.
#
# Licensed under the GPL, Version 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.gnu.org/licenses/gpl-3.0.txt
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ACAI - Acquia Cert Automatic Installer

This program installs LetsEncrpt certs into Acquia an environment defined in
either /etc/acai.conf or ~/.acai.conf.  See the README.md for more details.

usage: acai.py [-h] [-l | -b] environment

positional arguments:
  environment   The server environment defined in the config file to update.

optional arguments:
  -h, --help    show this help message and exit
  -l, --legacy  Install as a legacy certificate
  -b, --both    Install as both a normal and a legacy certificate
"""

from acapi2 import *

import argparse
import configparser
import datetime
import os
import sys
import time

# Load the configuration with each of the environments to support.
config = configparser.ConfigParser()
config.read(['/etc/acai.conf', os.path.expanduser('~/.acai.conf')]);

parser = argparse.ArgumentParser()
parser.add_argument('environment', help='The server environment to update defined in the config file.')
legacy_group = parser.add_mutually_exclusive_group()
legacy_group.add_argument('-l', '--legacy', help='Install as a legacy certificate', action="store_true")
legacy_group.add_argument('-b', '--both', help='Install as both a normal and a legacy certificate', action="store_true")
args = parser.parse_args()

# Fetch the creds for connecting to the Acquia environment
target = args.environment
api_key = config[target].get('api_key')
api_secret = config[target].get('api_secret')
application_uuid = config[target].get('application')
acquia_environment_name = config[target].get('acquia_environment')

# Validate we have everything we need.
if application_uuid is None:
  sys.exit('ERROR: Missing application in config')
if api_key is None or api_secret is None:
  sys.exit("ERROR: Missing API key or secret.")

# Read in all the certificates
cert_name = config[target].get('cert_name', target)
le_path = f"/etc/letsencrypt/live/{cert_name}"

# Find and read in all the certs.
try:
  with open(f"{le_path}/cert.pem") as f:
    new_cert = f.read()
  with open(f"{le_path}/privkey.pem") as f:
    new_private_key = f.read()
  with open(f"{le_path}/chain.pem") as f:
    new_ca_certs = f.read()
except Exception as e:
  sys.exit(f"ERROR: Could not open the cert files in {le_path}.\nVerify they exist and permissions are correct.\n" + str(e))

if (len(new_cert)==0):
  sys.exit("ERROR: Zero length cert.")

if (len(new_private_key)==0):
  sys.exit("ERROR: Zero length key.")

# Pre-flight complete, now we connect to Acquia.

# Connect to Acquia and fetch the application.
print("Connecting to Acquia...", end='', flush=True)
try:
  acquia = Acquia(api_key, api_secret)
  application = acquia.application(application_uuid)
  acquia_environment = application.environments().get(acquia_environment_name)
except Exception as e:
  sys.exit("ERROR: Could not connect to the Acquia environment: " + str(e))
print("done.")

if acquia_environment is None:
  sys.exit(f"ERROR: Could not find environment {acquia_environment_name} in {application['name']}.")

print(f"Fetching environment {acquia_environment_name}...", end='', flush=True)
environment_uuid = acquia_environment.get('id')
env = acquia.environment(environment_uuid)
print("done.")

cert_label = f"LetsEncrypt {target} " + str(datetime.date.today())
already_installed = False
for cert in env.get_ssl_certs():
  active = "Active" if cert['flags']['active'] else "Inactive"
  print(f"Found «{cert['label']}» expires {cert['expires_at']} ({active})")
  if cert['label'] == cert_label:
    already_installed = True

if already_installed:
  sys.exit(f"ERROR: Cert «{cert_label}» is already installed.")

# Install the new cert.
legacy = "legacy " if args.legacy else ""
print(f"Installing {legacy}cert named «{cert_label}»...", end='', flush=True)
try:
  env.install_ssl_cert(cert_label, new_cert, new_private_key, new_ca_certs, args.legacy)
  if args.both:
    print("legacy cert...", end='', flush=True)
    env.install_ssl_cert(cert_label, new_cert, new_private_key, new_ca_certs, True)
except Exception as e:
  sys.exit(f"\nERROR: Failed to install cert with error " + str(e))
print("Done.")

# Find and activate the cert.
if not args.legacy:
  # Activate the cert first before deactivating any of them.  Otherwise, we
  # may have a window where there are no certs active.  Ignore legacy certs.
  for cert in env.get_ssl_certs():
    if cert['label'] == cert_label and not cert['flags']['active'] and not cert['flags']['legacy']:
      print(f"Activating cert «{cert['label']}»...", end='', flush=True)
      env.activate_ssl_cert(cert['id'])
      print("done.")
  for cert in env.get_ssl_certs():
    if cert['label'] != cert_label and cert['flags']['active'] and not cert['flags']['legacy']:
      print(f"Deactivating cert «{cert['label']}»...", end='', flush=True)
      env.deactivate_ssl_cert(cert['id'])
      print("done.")
