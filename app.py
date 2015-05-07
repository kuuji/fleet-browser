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
    return redirect(url_for('show_dashboard', access_token=token))

@app.route('/dashboard')
def show_dashboard():
    token = request.args.get('access_token', '')
    if token != app.config.get('ACCESS_TOKEN'):
        return abort(401)

    units = requests.get('http://%s/fleet/v1/units' % FLEET_ENDPOINT).json().get("units", [])

    units_count = {'launched': 0, 'loaded': 0, 'inactive': 0, 'other': 0}
    # Count states
    for unit in units:
        if unit['currentState'] == 'launched':
            units_count['launched'] += 1
        elif unit['currentState'] == 'loaded':
            units_count['loaded'] += 1
        elif unit['currentState'] == 'inactive':
            units_count['inactive'] += 1
        else:
            units_count['other'] += 1

    states = requests.get('http://%s/fleet/v1/state' % FLEET_ENDPOINT).json().get("states", [])

    states_count = {'active': 0, 'inactive': 0, 'failed': 0, 'other': 0}
    templates = {}
    # Count states
    for state in states:
        if state['systemdActiveState'] == 'active':
            states_count['active'] += 1
        elif state['systemdActiveState'] == 'failed':
            states_count['failed'] += 1
        elif state['systemdActiveState'] == 'inactive':
            states_count['inactive'] += 1
        else:
            states_count['other'] += 1

        # Initialize templates dictionaries
        template_name = state['name'].split('@')[0]
        templates[template_name] = {'active': 0, 'inactive': 0, 'failed': 0, 'other': 0}

    # Count states per template
    for state in states:
        template_name = state['name'].split('@')[0]
        if state['systemdActiveState'] == 'active':
            templates[template_name]['active'] += 1
        elif state['systemdActiveState'] == 'failed':
            templates[template_name]['failed'] += 1
        elif state['systemdActiveState'] == 'inactive':
            templates[template_name]['inactive'] += 1
        else:
            templates[template_name]['other'] += 1

    # Transform data to be used by Highcharts
    templates_labels = sorted(templates.keys())
    templates_counts = [{'name': 'active', 'data': [], 'color': 'red'}, {'name': 'inactive', 'data': []},
                        {'name': 'failed', 'data': []}, {'name': 'other', 'data': []}]
    for label in templates_labels:
        templates_counts[0]['data'].append(templates[label]['active'])
        templates_counts[1]['data'].append(templates[label]['inactive'])
        templates_counts[2]['data'].append(templates[label]['failed'])
        templates_counts[3]['data'].append(templates[label]['other'])

    return render_template('dashboard.html',
                           states_count=states_count,
                           units_count=units_count,
                           templates_labels=templates_labels,
                           templates_counts=templates_counts,
                           token=token)

@app.route('/units')
def show_units():
    token = request.args.get('access_token', '')
    if token != app.config.get('ACCESS_TOKEN'):
        return abort(401)
    # Get units data
    data = requests.get('http://%s/fleet/v1/units' % FLEET_ENDPOINT).json()

    # Get machines data to get IPs matched from IDs
    machines_data = requests.get('http://%s/fleet/v1/machines' % FLEET_ENDPOINT).json()
    machines_ips = {}
    for machine in machines_data['machines']:
        machines_ips[machine['id']] = machine['primaryIP']

    # Transform machine ID into machine string: hash => simple_hash.../machine_IP
    for i in range(len(data['units'])):
        if 'machineID' in data['units'][i]:
            machine_id = data['units'][i]['machineID']
            machine_ip = machines_ips[machine_id]
            data['units'][i]['machine'] = '%s.../%s' % (machine_id[0:8], machine_ip)
        else: # If there's no machineID, use a single '-', like fleetctl
            data['units'][i]['machine'] = '-'

    return render_template('units.html', units=data.get("units", []), token=token)

@app.route('/state')
def show_state():
    token = request.args.get('access_token', '')
    if token != app.config.get('ACCESS_TOKEN'):
        return abort(401)
    # Get states data
    data = requests.get('http://%s/fleet/v1/state' % FLEET_ENDPOINT).json()

    # Get machines data to get IPs matched from IDs
    machines_data = requests.get('http://%s/fleet/v1/machines' % FLEET_ENDPOINT).json()
    machines_ips = {}
    for machine in machines_data['machines']:
        machines_ips[machine['id']] = machine['primaryIP']

    # Transform machine ID into machine string: hash => simple_hash.../machine_IP
    for i in range(len(data['states'])):
        machine_id = data['states'][i]['machineID']
        machine_ip = machines_ips[machine_id]
        data['states'][i]['machine'] = '%s.../%s' % (machine_id[0:8], machine_ip)

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
