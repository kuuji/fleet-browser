import requests
from flask import Flask, request, url_for, render_template, redirect
import os
import json

FLEET_ENDPOINT = os.environ.get('FLEET_ENDPOINT', '172.17.8.101:8080')

app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('show_state'))

@app.route('/units')
def show_units():
    data = requests.get('http://%s/fleet/v1/units' % FLEET_ENDPOINT).json()
    return render_template('units.html', units=data.get("units", []))

@app.route('/units/<name>', methods=['GET', 'PUT'])
def handle_unit(name):
    if request.method == 'GET':
        data = requests.get('http://%s/fleet/v1/units/%s' % (FLEET_ENDPOINT, name)).json()
        unit = {'name': data['name']}
        unit['json'] = data
        for i in range(len(unit['json']['options'])):
            unit['json']['options'][i]['value'] = unit['json']['options'][i]['value'].replace('"', '\\"')

        del unit['json']['currentState']
        del unit['json']['name']

        unit['json'] = json.dumps(unit['json'])

        unit['service'] = ''
        sections = {}
        for option in data['options']:
            sections[option['section']] = ''
        for option in data['options']:
            sections[option['section']] += '%s: %s\n' % (option['name'], option['value'])
        for section in reversed(sections.keys()):
            unit['service'] += '[%s]\n%s' % (section, sections[section])
            unit['service'] += '\n'
        return render_template('unit.html', unit=unit)
    elif request.method == 'PUT':
        res = requests.put('http://%s/fleet/v1/units/%s' % (FLEET_ENDPOINT, name), data=request.form.get('text'),
            headers={'content-type': 'application/json'})
        print res
        return 'Done'

@app.route('/state')
def show_state():
    data = requests.get('http://%s/fleet/v1/state' % FLEET_ENDPOINT).json()
    return render_template('state.html', states=data.get("states",[]))

@app.route('/machines')
def show_machines():
    data = requests.get('http://%s/fleet/v1/machines' % FLEET_ENDPOINT).json()
    return render_template('machines.html', machines=data.get("machines",[]))

if __name__ == '__main__':
    app.run(debug=True)
