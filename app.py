import requests
from flask import Flask, request, url_for, render_template, redirect, abort
import os
import json
import re

FLEET_ENDPOINT = os.environ.get('FLEET_ENDPOINT', '172.17.8.101:8080')

app = Flask(__name__)

if os.environ.get('ACCESS_TOKEN'):
    app.config['ACCESS_TOKEN'] = os.environ.get('ACCESS_TOKEN')
else:
    app.config['ACCESS_TOKEN'] = ''

def json_to_service_file(json_service):
    string_service = ''
    sections = {}
    for option in json_service:
        sections[option['section']] = ''
    for option in json_service:
        sections[option['section']] += '%s=%s\n' % (option['name'], option['value'])
    for section in reversed(sections.keys()):
        string_service += '[%s]\n%s' % (section, sections[section])
        string_service += '\n'
    return string_service

def service_file_to_json(string_service):
    json_service = []
    section = None
    for line in string_service.split('\n'):
        # Ignore comment lines
        if len(line) > 0 and line[0] == '#':
            continue

        # Find section
        find_section = re.search(r'\[([\w]+)\]', line)
        if find_section: # If found, start new section
            section = find_section.group(1)
        else: # Part of previous found section
            find_name_value = re.search(r'(.+)\s*=\s*(.+)', line)
            if find_name_value:
                name = find_name_value.group(1)
                value = find_name_value.group(2)
                json_service.append({
                    'section': section,
                    'name': name,
                    'value': value
                })
    return json_service

@app.route('/')
def index():
    token = request.args.get('access_token', '')
    if token != app.config.get('ACCESS_TOKEN'):
        return abort(401)
    return redirect(url_for('show_state', access_token=token))

@app.route('/units')
def show_units():
    token = request.args.get('access_token', '')
    if token != app.config.get('ACCESS_TOKEN'):
        return abort(401)
    data = requests.get('http://%s/fleet/v1/units' % FLEET_ENDPOINT).json()
    return render_template('units.html', units=data.get("units", []), token=token)

@app.route('/state')
def show_state():
    token = request.args.get('access_token', '')
    if token != app.config.get('ACCESS_TOKEN'):
        return abort(401)
    data = requests.get('http://%s/fleet/v1/state' % FLEET_ENDPOINT).json()
    return render_template('state.html', states=data.get("states",[]), token=token)

@app.route('/machines')
def show_machines():
    token = request.args.get('access_token', '')
    if token != app.config.get('ACCESS_TOKEN'):
        return abort(401)
    data = requests.get('http://%s/fleet/v1/machines' % FLEET_ENDPOINT).json()
    return render_template('machines.html', machines=data.get("machines",[]), token=token)

@app.route('/units/<name>', methods=['GET', 'PUT', 'DELETE'])
def handle_unit(name):
    token = request.args.get('access_token', '')
    if token != app.config.get('ACCESS_TOKEN'):
        return abort(401)

    if request.method == 'GET':
        data = requests.get('http://%s/fleet/v1/units/%s' % (FLEET_ENDPOINT, name)).json()
        try:
            unit = {'name': data['name']}
        except:
            abort(404)

        unit['service'] = json_to_service_file(data['options'])
        return render_template('unit.html', unit=unit, token=token)
    elif request.method == 'PUT':
        # Assembly data to send to API
        json_service = {
            'desiredState': request.form.get('desiredState'),
            'options': service_file_to_json(request.form.get('serviceFile'))
        }
        data = json.dumps(json_service)
        res = requests.put('http://%s/fleet/v1/units/%s' % (FLEET_ENDPOINT, name), data=data,
            headers={'content-type': 'application/json'})

        response_message = 'Failed'
        if res.status_code == 204:
            response_message = 'Modified'
        elif res.status_code == 201:
            response_message = 'Created'
        elif res.status_code == 400:
            response_message = 'Bad request'
        elif res.status_code == 409:
            response_message = 'Conflict'

        return response_message, res.status_code
    elif request.method == 'DELETE':
        res = requests.delete('http://%s/fleet/v1/units/%s' % (FLEET_ENDPOINT, name))
        response_message = 'Failed'
        status_code = res.status_code
        if res.status_code == 204:
            response_message = 'Deleted'
        elif res.status_code == 404:
            response_message = 'Not found'

        return response_message, status_code

if __name__ == '__main__':
    app.run('0.0.0.0', 5000, debug=True)
