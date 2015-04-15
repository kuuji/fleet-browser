# Fleet Browser

[Fleet API](https://github.com/coreos/fleet/blob/master/Documentation/api-v1.md) client running in the web.

For now it has view capabilities + plus the ability to put units from existing templates.

## Requirements

You need to have python installed and Flask. If you use pip, you can install Flask
with command

```
pip install Flask
```

You also need to set a environment variable called `FLEET_ENDPOINT` which points to your
Fleet API:

```
export FLEET_ENDPOINT=172.17.8.101:8080
```

## Usage

Just run
```
python app.py
```

The server should be up in `http://localhost:5000`.
