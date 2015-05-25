# Fleet Browser

[![Docker build](http://dockeri.co/image/cloudwalk/fleet-browser)](https://registry.hub.docker.com/u/cloudwalk/fleet-browser/)

This is a [Fleet's API](https://github.com/coreos/fleet/blob/master/Documentation/api-v1.md) web user interface.
Using this you can access data about your [CoreOS](https://coreos.com/) cluster and even create and launch new units in it.

![dashboard](https://rawgithub.com/cloudwalkio/fleet-browser/master/docs/images/dashboard.png)

## Enabling Fleet API on your CoreOS cluster

To use Fleet's API, you need to setup Fleet to serve the API over a network address.

If you're using CoreOS, this can be done through a extension to unit `fleet.socket`. For example, you can
add the following to your cloud-config file:

```
- name: fleet.socket
  drop-ins:
    - name: 30-ListenStream.conf
      content: |
        [Socket]
        ListenStream=8080
        Service=fleet.service
        [Install]
        WantedBy=sockets.target
```

## Usage

The service runs in a Docker container, so you can just start a container directly
or wrap this inside a unit file, if you're running the service in your CoreOS cluster,
for instance (which I suppose is the common scenario).

### Running it as a container directly

You'll just need to set the container's `FLEET_ENDPOINT` environment
variable. For example, if you running it on port `8080` on host `172.17.8.101`, you can run

```
docker run -d -e FLEET_ENDPOINT=172.17.8.101:8080 -p 5000:5000 cloudwalk/fleet-browser
```

The server should be up in `http://localhost:5000`. To login, use `admin` as both
username and password. See below how to set it to other values and to use two
factor authentication.

### Running it as a unit file

You may want to run this on your CoreOS cluster, in which case you can use the
following unit file:

```
[Unit]
Description=Expose Fleet API in a nice GUI
Requires=docker.service
After=docker.service  

[Service]
EnvironmentFile=/etc/environment
KillMode=none
TimeoutStartSec=0
Restart=always
RestartSec=10s
ExecStartPre=-/usr/bin/docker kill fleet-browser
ExecStartPre=-/usr/bin/docker rm fleet-browser
ExecStartPre=/usr/bin/docker pull cloudwalk/fleet-browser
ExecStart=/usr/bin/docker run --rm --name fleet-browser \
 -e FLEET_ENDPOINT=${COREOS_PRIVATE_IPV4}:8080 \
 -p 5000:5000 cloudwalk/fleet-browser
ExecStop=/usr/bin/docker stop fleet-browser
```

The server should be running in port 5000. To login, use `admin` as both
username and password. See below how to set it to other values.

Although this service file is a working one, we strongly recommend you to set a
password and enable two factor authentication, as explained in the following two
sections.

### [Optional] Set username and password

You can override the default login credentials, that uses `admin` for both username
and password:

```
docker run -d -e FLEET_ENDPOINT=172.17.8.101:8080 \
  -e USERNAME=admin -e PASSWORD=admin \
  -p 5000:5000 cloudwalk/fleet-browser
```

You can also enable two factor authentication. See the next section.

### [Optional] Enable Two Factor Authentication

We use [TOTP] as a 2FA mechanism. To enable it, you just need to set the `TOTP_KEY`
variable when running the container:

```
docker run -d -e FLEET_ENDPOINT=172.17.8.101:8080 -e TOTP_KEY=AWY7DDYXK5TK6FR6 \
  -p 5000:5000 cloudwalk/fleet-browser
```

Now you will be prompted to enter an authentication code after clicking the login
button.


#### Helpers

Obviously you'll want to use your own secure key. This can be done in Python quite
simple:

```
import base64
import os

print base64.b32encode(os.urandom(10))
```

Another thing you might want to do is to generate a QR-Code with your key encoded
to make it easier to register the service in some app, like [Authy], for instance:

```
qr "otpauth://totp/fleet-browser?secret=PUTYOURKEYHERE" > fleet-browser-qrcode.png
```

### Docker command to run this with all security layers

Wrapping everything you can set, you'll can run something like this:
```
docker run -d -e FLEET_ENDPOINT=172.17.8.101:8080 \
  -e USERNAME=admin -e PASSWORD=admin -e TOTP_KEY=AWY7DDYXK5TK6FR6 \
  -p 5000:5000 cloudwalk/fleet-browser
```

Just remember to set your own values to the variables specified by `-e`.

## Troubleshooting

### Fleet API is not reachable

You can get an error page if Fleet host is not reachable from
within the container.

This can happen if you're running CoreOS locally (on a Vagrant machine, for instance).
To solve this you may need to give the container access to it's host network,
using the `--net=host` flag:

```
docker run -d -e FLEET_ENDPOINT=172.17.8.101:8080 -p 5000:5000 --net=host cloudwalk/fleet-browser
```

## License

```
The MIT License (MIT)

Copyright (c) 2015 CloudWalk, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```


[TOTP]:http://www.wikiwand.com/en/Time-based_One-time_Password_Algorithm
[Authy]:https://www.authy.com/
