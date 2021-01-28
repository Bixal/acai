# ACAI - Acquia Cert Automatic Installer

This program installs LetsEncrypt SSL certificates into Acquia environments.


## Requirements

This program requires Python 3.x and the [Python Acquia Cloud API v2](https://github.com/pmatias/python-acquia-cloud-2) library with the [SSL management patch](https://github.com/pmatias/python-acquia-cloud-2/pull/33) applied.

## Configuration
The program looks in `/etc/acai.conf` and `~/.acai.conf` for environment definitions.  The config formats are in INI format.  Each environment is its own section in the config file, and the `DEFAULT` section provides values that are not overridden in a section.

Example:

```ini
[DEFAULT]
acquia_environment=prod
api_key=a26a25ad-69fb-4348-a7ac-bdd0a60849af
api_secret=TW9zdCBzZWN1cmUgcGFzc3dvcmQgaXMgPGVudGVyPi4=
application=7eff4747-4733-4070-9002-353c1dcdd090

[my-app.dev]
cert_name=myapp.bxdev.net
acquia_environment=dev

[my-app.stage]
cert_name=myapp.bxstage.net
acquia_environment=test

[another-app.prod]
application=7eff4747-4733-4070-9002-353c1dcdd090
api_key=070bdfe5-d106-40b0-a110-4882d8929669
api_secret=VmFjaGVzIGJsZXVlcyBsZSBtYXRpbiwgY2jDqXJpZS4=
cert_name=stage.another-app.com
acquia_environment=prod
```

* The INI section is only used by the acai.py app, and does not need to map to anything at Acquia or the site's hostname.

* The `api_key` and `api_secret` are generated in your Acquia account.  See the [Acquia documentation](https://docs.acquia.com/cloud-platform/develop/api/auth/) for details.

* The `cert_name` is the directory `/etc/letsencrypt/live/[cert_name]` that contains the cert, key, and chain.

* The `application` is the Application UUID.  You can find this by logging into Acquia Cloud and clicking "Product Keys" on the left.  It is also in the URL for your dashboard: `https://cloud.acquia.com/a/applications/[application-uuid]/`.

* The `acquia_environment` is the name of the envirionment at Acquia, typically one of `dev`, `test`, `prod` or `ra`.

* The `/etc/acai.conf` and `~/.acai.conf` files should have restrictive permissions.

## Usage

With the environments defined, the certs can be installed by running:

```
# acai.py my-app.dev
```

It doesn't have to run as root.  It needs to be able to read the letsencrypt certs (typically owned by root) and the `/etc/acai.conf` file to fetch the Acquia API creds.

This can be set up as a renewal hook triggered by certbot by editing the `/etc/letsencrypt/renew/[cert_name].conf` and adding a `renew_hook` to the `[renewalparams]` section.

```
[renewalparams]
renew_hook = /usr/bin/acai.py my-app.dev
```
