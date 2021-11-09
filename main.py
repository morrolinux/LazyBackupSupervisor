from flask import Flask, jsonify, request
from datetime import datetime


last_op_template = {"last_copy": None, "last_ver": None, "last_sync": None}
status_template = {"copy": None, "ver": None, "sync": None}
settings_template = {"copy_interval": 60*24, "ver_interval": 60*24, "sync_interval": 60*72}
stations = {"Pi4": {"master": {"settings": settings_template, "status": status_template, "last_op": last_op_template}}}


def traverse(d, path):
    res = d
    try:
        for k in path.split('/'):
            res = res[k]
    except KeyError as e:
        return jsonify({'KeyError': str(e)})

    return jsonify(res)


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
        stations[station][repo] = {"status": status_template, "settings": settings_template, "last_op": last_op_template}
    else:
        stations[station] = {repo: {"status": status_template, "settings": settings_template, "last_op": last_op_template}}

    return jsonify({"result": "OK"})
    

# example: curl -X POST http://localhost:8080/update -F station=Pi4 -F repo=repo1 -F operation=copy
@app.route('/update', methods=['POST'])
def update():
    repo = request.form.get('repo')
    station = request.form.get('station')
    operation = request.form.get('operation')

    stations[station][repo]["last_op"][operation] = str(datetime.now())

    return jsonify({"result": "OK"})


def is_elapsed(station, repo, operation, time_limit):
    last = datetime.strptime(stations[station][repo]["last_op"][operation], '%Y-%m-%d %H:%M:%S.%f')
    now = datetime.now()
    delta = now - last
    delta_hours = divmod(delta.seconds, 60)[0]
    return delta_hours >= time_limit


def check_elapsed():
    for station in stations:
        for repo in station.keys():
            pass


if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)
    # app.run(debug=True)
