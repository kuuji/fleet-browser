import json
import requests
import logging
import re

# Suppress annoying requests logs
logging.getLogger("requests").setLevel(logging.WARNING)

logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class FleetAPI(object):
    """ Helper for using Fleet API."""

    def __init__(self, fleet_endpoint):
        self.fleet_endpoint = fleet_endpoint

    def units(self, with_machines_ips=False):
        """ Return response from API /units. If with_machines_ips, units data get
            augmented with machines IPs to look like fleetctl output."""
        return self.__get_with_pagination('units', 'units', with_machines_ips)

    def states(self, with_machines_ips=False):
        """ Return response from API /state. If with_machines_ips, units data get
            augmented with machines IPs to look like fleetctl output."""
        return self.__get_with_pagination('state', 'states', with_machines_ips)

    def machines(self, with_machines_ips=False):
        """ Return response from API /machines. If with_machines_ips, units data get
            augmented with machines IPs to look like fleetctl output. """
        return self.__get_with_pagination('machines', 'machines', with_machines_ips)

    def units_stats(self):
        """ Compute units statistic. """
        units = self.units(with_machines_ips=False)

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

        return units_count

    def states_stats(self):
        """ Compute states statistics.
            Return a dict tuple: (states_count, templates_labels, templates_counts)
        """
        states = self.states(with_machines_ips=False)

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

        return states_count, templates_labels, templates_counts

    def get_unit(self, name):
        """ Get data unit with given <name> . """
        data = self.__get('units/%s' % name).json()

        try:
            unit = {'name': data['name']}
        except:
            return None

        unit['service'] = self.__json_to_service_file(data['options'])
        return unit

    def put_unit(self, name, service_file, desired_state):
        """ Submit unit with given name with given service_file and desired_state. """

        # Assembly data to send to API
        json_service = {
            'desiredState': desired_state,
            'options': self.__service_file_to_json(service_file)
        }
        data = json.dumps(json_service)
        res = self.__put('units/%s' % name, data=data,
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

    def delete_unit(self, name):
        """ Delete unit with given name. """
        res = self.__delete('units/%s' % name)

        response_message = 'Failed'
        if res.status_code == 204:
            response_message = 'Deleted'
        elif res.status_code == 404:
            response_message = 'Not found'

        return response_message, res.status_code

    def __get(self, address):
        """ Send GET request to /fleet/v1/<address>."""
        try:
            data = requests.get('http://%s/fleet/v1/%s' % (self.fleet_endpoint, address))
        except:
            raise
        return data

    def __put(self, address, data=None, headers={}):
        """ Send PUT request to /fleet/v1/<address>."""
        try:
            data = requests.put('http://%s/fleet/v1/%s' % (self.fleet_endpoint, address),
                                data=data, headers=headers)
        except:
            raise
        return data

    def __delete(self, address):
        """ Send DELETE request to /fleet/v1/<address>."""
        try:
            data = requests.delete('http://%s/fleet/v1/%s' % (self.fleet_endpoint, address))
        except:
            raise
        return data

    def __get_with_pagination(self, address, key, with_machines_ips=False):
        """ Get data from /fleet/v1/<address> with JSON key <key> handling
            pagination.
        """
        values = []

        data = self.__get(address).json()
        values += data.get(key, [])

        # Handle pagination
        next_page_token = data.get('nextPageToken')
        while next_page_token is not None:
            logger.debug('On the loop')
            data = self.__get('%s?nextPageToken=%s' % ( address, next_page_token)).json()
            values += data.get(key, [])
            next_page_token = data.get('nextPageToken')

        if with_machines_ips:
            machines_ips = self.__machines_ips()
            # Transform machine ID into machine string: hash => simple_hash.../machine_IP
            for i in range(len(values)):
                if 'machineID' in values[i]:
                    machine_id = values[i]['machineID']
                    machine_ip = machines_ips[machine_id]
                    values[i]['machine'] = '%s.../%s' % (machine_id[0:8], machine_ip)
                else: # If there's no machineID, use a single '-', like fleetctl
                    values[i]['machine'] = '-'
        return values

    def __machines_ips(self):
        """ Return dictionary with machines IDs as keys and IPs as values. """
        # Get machines data to get IPs matched from IDs
        machines = self.machines()

        machines_ips = {}
        for machine in machines:
            machines_ips[machine['id']] = machine['primaryIP']

        return machines_ips

    def __json_to_service_file(self, json_service):
        """ Convert given json_service into a string containing the original
            unit file.
        """

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

    def __service_file_to_json(self, string_service):
        """ Convert given string_service in a JSON ready to be submitted."""

        json_service = []
        section = None
        for line in string_service.split('\n'):
            # Ignore comment lines
            if len(line) > 0 and line[0] == '#':
                continue

            # Find section
            find_section = re.search(r'\[([\w-]+)\]', line)
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
                else: # Continuation of previous command
                    json_service[-1]['value'] += '\n%s' % line
        return json_service
