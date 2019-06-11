
from flask import Flask, request, jsonify

import dateparser
import datetime

import requests

import json


DATETIME_FORMAT = '%Y-%m-%d %H:%M'
DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M'
TRANSPORT_API_ROOT = 'http://transport.opendata.ch/v1/'


app = Flask(__name__)


@app.route('/', methods=['GET'])
def greeting():
    return "welcome to the transport bot", 200


@app.route('/webhook', methods=['POST'])
def webhook():

    data = request.get_json(force=True, silent=True)

    if data is None:
        return 'expect json', 400

    intent_name = data['queryResult']['intent']['displayName']
    if intent_name == 'stationboard':
        response_text = stationboard(data)
    elif intent_name == 'connection':
        response_text = connection(data)
    else:
        response_text = 'Sorry I did not understand.'

    response = {
        'fulfillmentText': response_text,
    }

    return jsonify(response)


def stationboard(request_data):

    station_name = request_data['queryResult']['parameters']['station_name']
    date = request_data['queryResult']['parameters']['date']
    time = request_data['queryResult']['parameters']['time']

    query_params = {
        'station': station_name,
        'datetime': parse_dialogflow_time(date, time).strftime(DATETIME_FORMAT),
        'limit': 3,
    }
    r = requests.get(TRANSPORT_API_ROOT + 'stationboard', params=query_params)
    response_data = json.loads(r.content.decode('utf-8'))

    answers = []
    for entry in response_data['stationboard']:
        name = entry['stop']['station']['name']
        departure = entry['stop']['departure']
        train_name = entry['name']
        destination = entry['to']
        answer = f'{train_name} to {destination} leaves {name} at {departure}'
        answers.append(answer)

    response_text = '\t'.join(answers)

    return response_text


def connection(request_data):

    source_name = request_data['queryResult']['parameters']['from']
    destination_name = request_data['queryResult']['parameters']['to']
    date = request_data['queryResult']['parameters']['date']
    time = request_data['queryResult']['parameters']['time']

    dtime = parse_dialogflow_time(date, time)
    query_params = {
        'from': source_name,
        'to': destination_name,
        'date': dtime.strftime(DATE_FORMAT),
        'time': dtime.strftime(TIME_FORMAT),
        'limit': 3,
    }
    r = requests.get(TRANSPORT_API_ROOT + 'connections', params=query_params)
    response_data = json.loads(r.content.decode('utf-8'))

    answer = f"Ok. The next {len(response_data['connections'])} connections"\
        f" from {response_data['from']['name']}"\
        f" to {response_data['to']['name']} are:"

    answers = [answer]
    for conn in response_data['connections']:
        departure_time = dateparser.parse(conn['from']['departure'])
        platform = conn['from']['platform']
        duration = conn['duration']
        answer = f"At {departure_time.strftime(TIME_FORMAT)}"\
            f" on platform {platform} taking {generate_duration(duration)}."
        answers.append(answer)

    response_text = '\t'.join(answers)

    return response_text


def generate_duration(duration):
    days, rest = duration.split('d')
    days = int(days)
    hours, minutes, seconds = tuple(map(int, rest.split(':')))

    parts = []
    if days > 0:
        if days == 1:
            parts.append('1 day')
        else:
            parts.append(f'{days} days')

    if hours > 0:
        if hours == 1:
            parts.append('1 hour')
        else:
            parts.append(f'{hours} hours')

    if minutes > 0:
        if minutes == 1:
            parts.append(('and ' if len(parts) > 0 else '') + '1 minute')
        else:
            parts.append(('and ' if len(parts) > 0 else '') + f'{minutes} minutes')

    return ' '.join(parts)


def parse_dialogflow_time(dialogflow_date, dialogflow_time):
    if type(dialogflow_time) is dict:
        return dateparser.parse(dialogflow_time['date_time'])
    else:
        now = datetime.datetime.now()
        date = dateparser.parse(dialogflow_date).date() if dialogflow_date != '' else now.date()
        time = dateparser.parse(dialogflow_time).time() if dialogflow_time != '' else now.time()
        return datetime.datetime.combine(date, time)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1818, debug=True)
