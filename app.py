from requests import ConnectionError
from flask import Flask, request, url_for, render_template, redirect, abort, session
import os
import json
import re
import pyotp
from functools import wraps
from fleet_api import FleetAPI

fleet =  FleetAPI(os.environ.get('FLEET_ENDPOINT', '172.17.8.101:8080'))

USERNAME = os.environ.get('USERNAME', 'admin')
PASSWORD = os.environ.get('PASSWORD', 'admin')
TOTP_KEY = os.environ.get('TOTP_KEY', None)
if TOTP_KEY is not None:
    TOTP = pyotp.TOTP(TOTP_KEY)
else:
    TOTP = None

app = Flask(__name__)
app.secret_key = os.urandom(24)

def logged_in(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('username', None) == USERNAME:
            if session.get('password', None) == PASSWORD:
                if session.get('totp', False):
                    return f(*args, **kwargs)

        return redirect(url_for('login'))
    return decorated_function

@app.route('/ping')
def ping():
    return 'OK', 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != USERNAME or request.form['password'] != PASSWORD:
            error = 'Invalid Credentials. Please try again.'
        else:
            session['username'] = USERNAME
            session['password'] = PASSWORD
            if TOTP is not None:
                return redirect(url_for('totp'))
            else:
                # Set totp to True if no key specified
                session['totp'] = True
                return redirect(url_for('index'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('password', None)
    session.pop('totp', None)
    return redirect(url_for('index'))

@app.route('/totp', methods=['GET', 'POST'])
def totp():
    error = None
    if request.method == 'POST':
        try:
            token = int(request.form.get('totp-token', -1))
            if not TOTP.verify(token):
                error = 'Wrong TOTP token.'
            else:
                session['totp'] = True
                return redirect(url_for('index'))
        except ValueError:
            error = 'The token is a 6 digit number.'
    return render_template('totp.html', error=error)

@app.route('/')
@logged_in
def index():
    return redirect(url_for('show_dashboard'))

@app.route('/dashboard')
@logged_in
def show_dashboard():
    try:
        units_count = fleet.units_stats()
        states_count, templates_labels, templates_counts = fleet.states_stats()
    except Exception, e:
        return render_template('error.html', error=e)

    return render_template('dashboard.html',
                           states_count=states_count,
                           units_count=units_count,
                           templates_labels=templates_labels,
                           templates_counts=templates_counts)

@app.route('/units')
@logged_in
def show_units():
    # Get units data augmented with machines IPs to look like fleetctl output
    try:
        units = fleet.units(with_machines_ips=True)
    except Exception, e:
        return render_template('error.html', error=e)

    return render_template('units.html', units=units)

@app.route('/state')
@logged_in
def show_state():
    # Get state data
    try:
        states = fleet.states(with_machines_ips=True)
    except Exception, e:
        return render_template('error.html', error=e)

    return render_template('state.html', states=states)

@app.route('/machines')
@logged_in
def show_machines():
    # Get machines data
    try:
        machines = fleet.machines(with_machines_ips=False)
    except Exception, e:
        return render_template('error.html', error=e)

    return render_template('machines.html', machines=machines)

@app.route('/units/<name>', methods=['GET', 'PUT', 'DELETE'])
@logged_in
def handle_unit(name):
    if request.method == 'GET':
        try:
            unit = fleet.get_unit(name)
        except Exception, e:
            return render_template('error.html', error=e)

        if unit is None:
            abort(404)

        return render_template('unit.html', unit=unit)
    elif request.method == 'PUT':
        try:
            response_message, status_code = fleet.put_unit(name,
                request.form.get('serviceFile'), request.form.get('desiredState'))
        except Exception, e:
            return render_template('error.html', error=e)

        return response_message, status_code
    elif request.method == 'DELETE':
        try:
            response_message, status_code = fleet.delete_unit(name)
        except Exception, e:
            return render_template('error.html', error=e)

        return response_message, status_code

if __name__ == '__main__':
    app.run('0.0.0.0', 5000, debug=True)
