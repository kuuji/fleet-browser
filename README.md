# Fleet Browser

[![Docker build](http://dockeri.co/image/cloudwalk/fleet-browser)](https://registry.hub.docker.com/u/cloudwalk/fleet-browser/)

[Fleet API](https://github.com/coreos/fleet/blob/master/Documentation/api-v1.md) client running in the web.

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

### Running is as a container directly

You'll just need to set the container's `FLEET_ENDPOINT` environment
variable. For example, if you running it on port `8080` on host `172.17.8.101`, you can run

```
docker run -d -e FLEET_ENDPOINT=172.17.8.101:8080 -p 5000:5000 cloudwalk/fleet-browser
```

The server should be up in `http://localhost:5000`.

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
ExecStart=/usr/bin/docker run --rm --name fleet-browser -e FLEET_ENDPOINT=${COREOS_PRIVATE_IPV4}:8080 \
  -p 5000:5000 cloudwalk/fleet-browser
ExecStop=/usr/bin/docker stop fleet-browser
```

### [Optional] URL authentication

There is a simple authentication mechanism using an URL parameter `access_token`.
To enable it, just set a container's environment variable called `ACCESS_TOKEN`.
For instance:

```
docker run -d -e FLEET_ENDPOINT=172.17.8.101:8080 -e ACCESS_TOKEN=ishallpass \
  -p 5000:5000 cloudwalk/fleet-browser
```

Then, to access the server, you should do something like
`http://localhost:5000/?access_token=ishallpass`.

## Troubleshooting

If you get some server error, it may be due to the fact that your Fleet host is not reachable from
within the container.

If you're running CoreOS locally (on a Vagrant machine, for instance), you may need to give
the container access to it's host network, using the `--net=host` flag:

```
docker run -d -e FLEET_ENDPOINT=172.17.8.101:8080 -p 5000:5000 --net=host cloudwalk/fleet-browser
```
