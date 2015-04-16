# Fleet Browser

[Fleet API](https://github.com/coreos/fleet/blob/master/Documentation/api-v1.md) client running in the web.

For now it has view capabilities + plus the ability to put units from existing templates.

## Requirements

### Python dependencies

You need to have python installed and Flask. If you use pip, you can install Flask
with command

```
pip install Flask
```


### Environment setup

To use Fleet's API, you need to setup Fleet to serve the API over a network address.
This can be done through a extension to unit `fleet.socket`. For example, you can
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

You'll just need to set a environment variable called `FLEET_ENDPOINT` which points to your
Fleet API, for example:

```
export FLEET_ENDPOINT=172.17.8.101:8080
```

## Usage

Just run
```
python app.py
```

The server should be up in `http://localhost:5000`.
