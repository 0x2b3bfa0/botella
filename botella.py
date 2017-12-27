#!/usr/bin/env python3

from flask import Flask, request, make_response, Response
from slackclient import SlackClient
from pprint import pprint

import randomcolor
import json
import os


SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_VERIFICATION_TOKEN = os.environ["SLACK_VERIFICATION_TOKEN"]

color = randomcolor.RandomColor()
slack_client = SlackClient(SLACK_BOT_TOKEN)
app = Flask(__name__)
options = dict() 

questions = [
    {"text": "¿cuánto es dos y dos?",
     "options": ["4", "6", "22", "El número varía según la cantidad de grajas sobrevolando las hoces, el río o el pinar"],
     "answer": [2, "si fuera 2 más 2, sería 4, pero *y* concatena"]}
]

def ask(id, text=None, hide=False):
    data = {
        "fallback": "Pregunta",
        "attachment_type": "default",
        "text":  text or questions[id]["text"],
        "color": questions[id]["color"],
        "callback_id": str(id)
    }

    if not hide:
        data["actions"] = [
            {
                "name": "list",
                "text": "Selecionar...",
                "type": "select",
                "data_source": "external"
            }
        ]
    return [data]

for index, question in enumerate(questions):
    options[str(index)] = {"options": [
        {"text": option, "value": str(index)}
        for index, option in enumerate(question["options"])
    ]}
    questions[index]["color"] = color.generate()[0]
    slack_client.api_call(
      "chat.postMessage",
      channel="U7EEV8AMQ",
      #channel="C8KJBFGR0",
      text="",
      attachments=ask(index, text="Pregunta: " + questions[index]["text"]),
      as_user=True
    )

#imList=slack_client.api_call("im.list")
#for user in imList['ims']:
#    pprint(user)
#    info = slack_client.api_call("users.info", user=user['user'])
#    pprint(info)


@app.route("/slack/interactive_data", methods=["POST"])
def message_options():
    data = json.loads(request.form["payload"])
    return Response(json.dumps(options[data["callback_id"]]), mimetype='application/json')

@app.route("/slack/interactive", methods=["POST"])
def message_actions():
    data = json.loads(request.form["payload"])
    selection = int(data["actions"][0]["selected_options"][0]["value"])
    id = int(data["callback_id"])

    response = slack_client.api_call(
      "chat.postMessage",
      channel=data["channel"]["id"],
      ts=data["message_ts"],
      text="",
      attachments=ask(id, hide=True, text="Pregunta: " + questions[id]["text"] + "\n" + "Tu respuesta: " + questions[id]["options"][selection] + "\nSolución: " + "¡correcto! " if selection == questions[id]["answer"][0] else "¡incorrecto! " + questions[id]["answer"][1]),
      replace_original=True
    )

    return make_response("", 200)



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050)
