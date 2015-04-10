import requests
from flask import Flask, request, url_for, render_template
import os

FLEET_ENDPOINT = os.environ.get('FLEET_ENDPOINT', '172.17.8.101:8080')

app = Flask(__name__)

@app.route('/units')
def show_units():
    data = requests.get('http://%s/fleet/v1/units' % FLEET_ENDPOINT)
    return render_template('units.html', units=data.json()["units"])

@app.route('/units/<name>')
def show_unit(name):
    data = requests.get('http://%s/fleet/v1/units/%s' % (FLEET_ENDPOINT, name))
    return render_template('unit.html', unit=data.json())

@app.route('/state')
def show_state():
    data = requests.get('http://%s/fleet/v1/state' % FLEET_ENDPOINT)
    return render_template('state.html', states=data.json()["states"])

@app.route('/machines')
def show_machines():
    data = requests.get('http://%s/fleet/v1/machines' % FLEET_ENDPOINT)
    return render_template('machines.html', machines=data.json()["machines"])

if __name__ == '__main__':
    app.run(debug=True)
