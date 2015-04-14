# Fleet Browser

[Fleet API](https://github.com/coreos/fleet/blob/master/Documentation/api-v1.md) client running in the web.

For now it has view capabilities + plus the ability to put units from existing templates.

## Usage

You need to set a environment variable called `FLEET_ENDPOINT` which points to your
Fleet API:

```
export FLEET_ENDPOINT=172.17.8.101:8080
python app.py
```

It should be up in `http://localhost:5000`.
