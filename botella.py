#!/usr/bin/env python3

from flask import Flask, request, make_response, Response
from slackclient import SlackClient
from pprint import pprint

import threading
import schedule
import time
import json
import re
import os


app = Flask(__name__)
SLACK_VERIFICATION_TOKEN = os.environ["SLACK_VERIFICATION_TOKEN"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
slack_client = SlackClient(SLACK_BOT_TOKEN)
questions = dict()
messages = []

users = [user["id"] for user in slack_client.api_call("users.list")["members"]]

denada=re.compile('.*(d+[^a-z]*[eé]*[^a-z]*n+[^a-z]*[aá]+[^a-z]*d+[^a-z]*[aá]+).*')
ytanto=re.compile('.*(y*[^a-z]*t+[^a-z]*[áa]+[^a-z]*n+[^a-z]*t+[^a-z]*[oó]+).*')
hola=re.compile('[^a-z]*hola[^a-z]*')

def message(event):
    try:
        with open('messages.json', 'r') as fp:
            global messages
            messages = json.load(fp)
    except:
            assert False
    messages += [event]
    try:
        with open('messages.json', 'w') as fp:
            json.dump(messages, fp)
    except:
        assert False
    if event["user"] == "U8KNJAHEZ":
        return None
    text = event["text"].casefold()
    result="No te entiendo. Puedes quejarte a <@U7EEV8AMQ>."
    if denada.match(text) is not None or ytanto.match(text) is not None:
        result = "¡Detesto las majaderías! :smiling_imp:"
    if hola.match(text) is not None:
        result = "¡Hola, mundo!"
     
    response = slack_client.api_call(
        "chat.postMessage",
        channel=event["channel"],
        text=result,
        as_user=True,
        link_names=True
    )

def ask(question, answer=None):
    data = {
        "fallback": "Pregunta",
        "attachment_type": "default",
        "callback_id": question["index"],
        "color": "warning",
        "fields": [{
            "title": question["text"],
            "short": False
        }]
    }

    confirm = {
        "title": "¿Enviar respuesta?",
        # "text": "Esta decisión es irreversible",
        "dismiss_text": "No",
        "ok_text": "Sí"
    }

    data["actions"] = [
        {
            "name": "answer",
            "text": option,
            "type": "button",
            "value": str(index),
            # "confirm": confirm,
        }
        for index, option in enumerate(question["options"])
    ]

    if answer is not None:
        right = answer == question["answer"][0]
        for index, _ in enumerate(data["actions"]):
            data["actions"][index]["style"] = "primary" if index == question["answer"][0] else "danger"
        data["fields"][0]["value"] = "{}, {}".format("Sí" if right else "No", question["answer"][1])
        data["color"] = "good" if right else "danger"

    return [data]

@app.route("/listening", methods=["GET", "POST"])
def listening():
    data = json.loads(request.data)
    if "challenge" in data:
        return Response(data["challenge"], mimetype='application/json')
    if data["token"] != SLACK_VERIFICATION_TOKEN:
        return make_response("wrong token", 500)
    if data["event"]["type"] == "message":
        response = message(data["event"])
    return make_response("", 200)

@app.route("/slack/interactive_data", methods=["POST"])
def message_options():
    data = json.loads(request.form["payload"])
    return Response(json.dumps(data["callback_id"]), mimetype='application/json')

@app.route("/slack/interactive", methods=["POST"])
def message_actions():
    data = json.loads(request.form["payload"])
    answer = int(data["actions"][0]["value"])
    id = int(data["callback_id"])

    pprint(data["user"]["id"])
    pprint(questions)
    if data["user"]["id"] in [user[0] for user in questions[id]["users"]]:
        return make_response("", 200)

    response = slack_client.api_call(
      "chat.update",
      channel=data["channel"]["id"],
      ts=data["message_ts"],
      text="",
      attachments=ask(questions[id], answer),
      replace_original=True
    )

    questions[id]["users"] += [(data["user"]["id"], answer == questions[id]["answer"][0])]

    try:
        with open('data.json', 'w') as fp:
            json.dump(questions, fp)
    except:
        assert False

    return make_response("", 200)

def job():
    try:
        with open('data.json', 'r') as fp:
            global questions
            questions = json.load(fp)
    except:
            assert False

    try:
        with open('counter.json', 'r') as fp:
            counter = json.load(fp)[0]
            print("Counter:", counter)
    except:
            assert False


    try:
        for user in users:
            slack_client.api_call(
                "chat.postMessage",
                channel=user,
                text="",
                attachments=ask(questions[counter]),
                as_user=True
            )
        counter += 1
        try:
            with open('counter.json', 'w') as fp:
                json.dump([counter], fp)
        except:
            assert False
    except: print("Error: no more questions")

    return

schedule.every().day.at("8:00").do(job)
schedule.run_continuously()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050)
