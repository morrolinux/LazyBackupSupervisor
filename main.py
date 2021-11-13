from flask import Flask, jsonify, request
from datetime import datetime
import signal
import threading
import json
import sys


terminating = threading.Event()
last_op_template = {"copy": None, "ver": None, "sync": None}
status_template = {"copy": None, "ver": None, "sync": None}
interval_template = {"copy": 60*24, "ver": 60*24, "sync": 60*72}
stations_template = {"Pi4": {"master": {"interval": interval_template, "status": status_template, "last_op": last_op_template}}}
stations = None
failed_jobs = set()
failed_jobs_notified = set()


def signal_handler(sig, frame):
    print('terminating...')
    terminating.set()
    save_status()
    sys.exit(0)


def traverse(d, path):
    res = d
    try:
        for k in path.split('/'):
            res = res[k]
    except KeyError as e:
        return jsonify({'KeyError': str(e)})

    return jsonify(res)


def save_status():
    with open('stations.json', 'w') as fp:
        json.dump(stations, fp)

def load_status():
    with open('stations.json', 'r') as fp:
        stations = json.load(fp)

app = Flask(__name__)

@app.route('/')
def index():
    return "Welcome."

@app.route('/status', methods=['GET'])
def status_all():
    return jsonify({'stations': stations})

@app.route('/status/<path:path>', methods=['GET'])
def status_station(path):
    return traverse(stations, path)


# example: curl -X POST http://localhost:8080/add -F station=Pi4 -F repo=repo1
@app.route('/add', methods=['POST'])
def create():
    repo = request.form.get('repo')
    station = request.form.get('station')

    if station in stations.keys():
        stations[station][repo] = {"status": status_template, "interval": interval_template, "last_op": last_op_template}
    else:
        stations[station] = {repo: {"status": status_template, "interval": interval_template, "last_op": last_op_template}}

    save_status()

    return jsonify({"result": "OK"})
    

# example: curl -X POST http://localhost:8080/update -F station=Pi4 -F repo=repo1 -F operation=copy
@app.route('/update', methods=['POST'])
def update():
    repo = request.form.get('repo')
    station = request.form.get('station')
    operation = request.form.get('operation')

    stations[station][repo]["last_op"][operation] = str(datetime.now())

    save_status()

    return jsonify({"result": "OK"})


def is_elapsed(station, repo, operation, time_limit):
    try:
        last = datetime.strptime(stations[station][repo]["last_op"][operation], '%Y-%m-%d %H:%M:%S.%f')
    except Exception:
        return True

    now = datetime.now()
    delta = now - last
    delta_hours = divmod(delta.seconds, 60)[0]
    return delta_hours >= time_limit


def check_elapsed():
    for station in stations:
        for repo in stations[station]:
            for operation in stations[station][repo]["last_op"]:
                ts = stations[station][repo]["last_op"][operation]
                time_limit = stations[station][repo]["interval"][operation]
                error = is_elapsed(station, repo, operation, time_limit)
                stations[station][repo]["status"][operation] = not error

                item = (station, repo, operation)
                if error:
                    if not item in failed_jobs_notified:
                        failed_jobs.add(item)
                elif item in failed_jobs_notified:
                    failed_jobs_notified.remove(item)


def status_service():
    import time
    while not terminating.is_set():
        check_elapsed()
        time.sleep(1)
    save_status()


if __name__ == "__main__":
    from waitress import serve
    # check_elapsed()

    signal.signal(signal.SIGINT, signal_handler)

    try:
        load_status()
    except FileNotFoundError as e:
        print("no previous saved status to load..")
    except json.decoder.JSONDecodeError as e:
        print("status file is broken.")

    stations = stations_template if stations is None else stations

    threading.Thread(target=status_service).start()
    serve(app, host="0.0.0.0", port=8080)
    # app.run(debug=True)
