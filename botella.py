#!/usr/bin/env python3

from flask import Flask, request, make_response, Response
from slackclient import SlackClient
from pprint import pprint
import subprocess
import threading
import schedule
import hashlib
import time
import hmac
import json
import sys
import os
import re

# QUESTION: Can anybody implement global stats with usernames? here I leave a test code snippet.
# users=['U7EEV8AMQ'] # Helio Machado
# users = [user['id'] for user in slack_client.api_call('users.list')['members']]

SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']
SLACK_VERIFICATION_TOKEN = os.environ['SLACK_VERIFICATION_TOKEN']
GITHUB_SECRET = bytes(os.environ['GITHUB_SECRET'], 'UTF-8')

app = Flask(__name__)
slack_client = SlackClient(SLACK_BOT_TOKEN)


questions = dict()
def save_questions():
    global questions
    with open('questions.json', 'w') as fp:
        json.dump(questions, fp, indent=4, sort_keys=True)
def load_questions():
    global questions
    with open('questions.json', 'r') as fp:
        questions = json.load(fp)
messages = []
def save_messages():
    global messages
    with open('messages.json', 'w') as fp:
        json.dump(messages, fp, indent=4, sort_keys=True)
def load_messages():
    global messages
    with open('messages.json', 'r') as fp:
        messages = json.load(fp)
counter = dict()
def save_counter():
    global counter
    with open('counter.json', 'w') as fp:
        json.dump(counter, fp, indent=4, sort_keys=True)
def load_counter():
    global counter
    with open('counter.json', 'r') as fp:
        counter = json.load(fp)

pending = dict()
def save_pending():
    global pending
    with open('pending.json', 'w') as fp:
        json.dump(pending, fp, indent=4, sort_keys=True)
def load_pending():
    global pending
    with open('pending.json', 'r') as fp:
        pending = json.load(fp)

def parse_files():
    load_questions()
    save_questions()
    load_counter()
    save_counter()
    load_pending()
    save_pending()

def verify_hash(data, signature):
    mac = hmac.new(GITHUB_SECRET, msg=data, digestmod=hashlib.sha1)
    return hmac.compare_digest('sha1=' + mac.hexdigest(), signature)

def message(event):
    global messages
    messages += [event]
    save_messages()

    if not 'user' in event: return None # Sanity check for global events
    if 'edited' in event: return None  # Don't answer to edited messages
    if event['user'] == 'U8KNJAHEZ': return None  # Bot response ignored (FIXME hardcoded)
    text = event['text'].casefold()

    answer = "No estoy segura de haberte entendido. Puedes quejarte ante <@U7EEV8AMQ> para que me reprograme. Si lo que quieres es responder a una pregunta que te he hecho, pulsa sobre la respuesta, que para eso soy interactiva."
    if re.compile('[^a-z]*hola[^a-z]*(mundo[^a-z]*)?').match(text) is not None:
        answer = "¡Hola, mundo!"
    if re.compile('[^a-z]*hola[^a-z]*@?botella[^a-z]*').match(text) is not None:
        name = slack_client.api_call("users.info", user=event["user"])["user"]["real_name"]
        answer = "¡Hola, {}!".format(name)
    if re.compile('[^a-z]*hola[^a-z]*@?botel?[ly]ita[^a-z]*').match(text) is not None:
        name = slack_client.api_call("users.info", user=event["user"])["user"]["real_name"]
        answer = "¡Hola, {} (ponle el diminutivo más ridículo y ñoño que conozcas)!".format(name)
    if re.compile('(.*(piensas|dime|cuéntame|opinar|pensar).*|.*[?][^a-z]*)').match(text) is not None:
        answer = "Aún no sé pensar ni responder preguntas de forma libre, pero me gustaría aprender. :smile: Si quieres enseñarme... sólo te hace falta saber un poquito de <https://www.python.org|Python>, <https://www.tensorflow.org|TensorFlow> y <https://spacy.io|spaCy>. Puedes encontrar <https://github.com/0x2b3bfa0/botella|mi código> en GitHub."
    if re.compile('.*[^a-z]*(qu[ée]|[c[óo]m[óo]|[c[úu][áa]ndo|[d[óo]nd[ée]|q[uú][eé]|[c[uú][áa]l|qu[íi][eé]n|[c[uú][aá]nto).*').match(text) is not None:
        answer = "Lo siento, no sé cómo responderte. Si lo que me has preguntado es tan obvio, prueba a quejarte a mi creador (<@U7EEV8AMQ>) para que me enseñe a contestarlo."
    if re.compile('.*te[^a-z]*llamas.*').match(text) is not None or re.compile('.*tu[^a-z]*nombre.*').match(text) is not None or re.compile('.*(qu|k)i[eé]n[^a-zA-Z]+eres.*').match(text) is not None:
        answer = "Me llamo <@botella>. Lo peor de todo es que ya lo sabías."
    if re.compile('¿?.*tutora.*\?[^a-zA-Z]*').match(text) is not None:
        answer = "La tutora es muchísimo más inteligente que yo, así que mejor pregúntale a ella. Es muy amable y puede atenderte los miércoles desde las 17:15 hasta las 18:10, o incluso al finalizar su clase."
    if re.compile('.*(edad|años)[^a-z]*tienes.*').match(text) is not None or re.compile('.*tienes.*(edad|años).*[?].*').match(text) is not None:
        answer = "No sé. Pregúntale al que me programó."
    if re.compile('.*[^a-z]*(notas?|punt(os|ua((da|do)|(ci[oó]n))))[^a-z]*').match(text) is not None:
        well = sum([1 if value is True else 0 for value in counter[event["user"]]])
        answer = "Tu nota es: {}/{} ({}%)".format(well, len(counter[event["user"]]), int((well/len(counter[event["user"]]))*100))
    if re.compile('.*(hacer|poner|preguntar|añadir|agregar|crear|programar|introducir)(le)?[^a-z]*((alg)?una)?[^a-z]*(una|nuevas|nueva|una[^a-z]*nueva|m[áa]s)[^a-z]*(pregunta)?.*').match(text) is not None:
        answer = "Lo siento, aún no puedo modificarme yo sola. Si quieres poner más preguntas, habla con <@U7EEV8AMQ>"
    if re.compile('.*[^a-z]*gr[aá]c[ií][aá]s[^?]*').match(text) is not None:
        answer = "¡No hay de qué!"
    if re.compile('[^a-z¿]*te\s+(odio|aborr?e[zs]co|quiero)[^a-z?]*').match(text) is not None:
        answer = "¡Yo también!"
    if re.compile('[^a-z¿]*no\s+te\s+quiero[^a-z?]*').match(text) is not None:
        answer = "¿Qué he hecho para que me digas eso?"
    if re.compile('.*(d+[^a-z]*[eé]*[^a-z]*n+[^a-z]*[aá]+[^a-z]*d+[^a-z]*([aá]|[is])+).*').match(text) is not None or re.compile('.*(y*[^a-z]*t+[^a-z]*[áa]+[^a-z]*n+[^a-z]*t+[^a-z]*[oó]+).*').match(text) is not None:
        answer = "¡Detesto las majaderías! :smiling_imp:"
    elif event["user"] == "U7G0C8L02":
        answer += " ¡Gracias!" # Trigger "de nada" from @MaríaBot

    slack_client.api_call(
        "chat.postMessage",
        channel=event["channel"],
        text=answer,
        as_user=True,
        link_names=True
    )

def ask(question, answer=None):
    data = {
        "fallback": "Pregunta",
        "attachment_type": "default",
        "callback_id": questions.index(question),
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
        correct = answer == question["answer"][0]
        right, wrong = "Efectivamente", "No"
        if "prepend" in question:
            right, wrong = question["prepend"]
        for index, _ in enumerate(data["actions"]):
            data["actions"][index]["style"] = "primary" if index == question["answer"][0] else "danger"
        data["fields"][0]["value"] = "{}, {}".format(right if correct else wrong, question["answer"][1])
        data["color"] = "good" if correct else "danger"

    return [data]

def answer_callback(data):
    sorry_text = "No sé qué más te puedo preguntar. Te avisaré cuando se me ocurra algo."
    answer = int(data["actions"][0]["value"])
    index = int(data["callback_id"])
    user = data["user"]["id"]

    if not user in counter:
        counter[user] = []
    if len(counter[user]) != index:
        return

    counter[user] += [True if questions[index]["answer"][0] == answer else answer]
    user_index = len(counter[user])
    save_counter()

    slack_client.api_call(
      "chat.update",
      channel=data["channel"]["id"],
      ts=data["message_ts"],
      text="",
      attachments=ask(questions[index], answer),
      replace_original=True
    )

    if user_index < len(questions):
        slack_client.api_call(
            "chat.postMessage",
            channel=user,
            text="",
            attachments=ask(questions[user_index]),
            as_user=True
        )
    else:
        pending[user] = True
        save_pending()
        slack_client.api_call(
            "chat.postMessage",
            channel=user,
            text=sorry_text,
            attachments=[],
            as_user=True
        )

def watchdog():
    global questions
    global pending
    load_pending()
    load_counter()
    for user in list(pending):
        try:
            index = len(counter[user])
        except:
            index = 0
        print(user, index, len(questions), flush=True, file=sys.stderr)
        if pending[user] and index < len(questions):
            slack_client.api_call(
                "chat.postMessage",
                channel=user,
                text="",
                attachments=ask(questions[index]),
                as_user=True
            )
            pending.pop(user, None)
            save_pending()

@app.errorhandler(404)
def not_found(error):
    """Handbook-style narcissism ;-)"""
    return Response("""Designed and developed by Helio Machado <0x2b3bfa0>
                       for the José María Cruz Novillo Arts School at Cuenca (Spain)""")

@app.route("/api", methods=["GET", "POST"])
def api():
    """/api?method=<method> with JSON post arguments"""
    return # So good to be true. Enabled only when testing. Keep trying!
    try:
        method = request.args.get('method')
        if request.data:
            data = json.loads(request.data)
            response = slack_client.api_call(method, **data)
        else:
            response = slack_client.api_call(method)
    except:
        return Response('{"error": true}', mimetype='application/json')
    else:
        return Response(json.dumps(response), mimetype='application/json')

@app.route("/git", methods=["POST"])
def git():
    data = json.loads(request.data)
    signature = request.headers.get('X-Hub-Signature')
    if not verify_hash(request.data, signature):
        return make_response("{'msg': 'invalid hash'}", 403)
    if request.headers.get('X-GitHub-Event') == "ping":
        return Response("{'msg': 'Ok'}", mimetype='application/json')
    elif request.headers.get('X-GitHub-Event') == "push":
        if len(data["commits"]) == 0:
            return Response("{'msg': 'ignored'}", mimetype='application/json')
        if not data['commits'][0]['distinct']:
            return Response("{'msg': 'ignored'}", mimetype='application/json')
        try:
            cmd_output = subprocess.check_output(['git', 'pull'],)
            cmd_output = subprocess.check_output(['chown', '-R', os.environ['OWNERSHIP'] , '.'],)
            print(slack_client.api_call("chat.postMessage",
                                  channel="U7EEV8AMQ", # Helio Machado
                                  text="GitHub commit deployment successful.",
                                  as_user=True),file=sys.stderr)
            subprocess.check_output(['systemctl', 'restart', 'botella'],)
            return json.dumps({'msg': str(cmd_output)})
        except subprocess.CalledProcessError as error:
            slack_client.api_call("chat.postMessage",
                                  channel="U7EEV8AMQ", # Helio Machado
                                  text="GitHub commit deployment failed: `{}`".format(error),
                                  as_user=True)
            return json.dumps({'msg': str(error.output)})
        else:
            return json.dumps({'msg': 'nothing to commit'})


@app.route("/get", methods=["GET"])
def get():
    """/get?item=3 item is optional"""
    item = request.args.get('item', type=int)
    if item is None:
        return Response(json.dumps(questions, indent=4, sort_keys=True), mimetype='application/json')
    else:
        try:
            response = Response(json.dumps(questions[item], indent=4, sort_keys=True), mimetype='application/json')
        except:
            response = Response('{"error": true}', mimetype='application/json')
        return response

@app.route("/refresh", methods=["GET"])
def refresh():
    """/refresh reloads the question table"""
    parse_files()
    return make_response("", 200)

@app.route("/add", methods=["POST"])
def add():
    try:
        global questions
        data = json.loads(request.data)
        assert type(data["text"]) is str
        assert type(data["answer"][0]) is int
        assert type(data["answer"][1]) is str
        assert type(data["options"]) is list
        assert type(data["answer"]) is list
        assert len(data["answer"]) == 2
        for option in data["options"]: assert type(option) is str
        question = {"text": data["text"], "options": data["options"], "answer": data["answer"]}
        if "prepend" in data:
            assert type(data["prepend"]) is list
            assert len(data["prepend"]) == 2
            for value in data["prepend"]: assert type(value) is str
            question["prepend"] = data["prepend"]
        if "tags" in data:
            assert type(data["tags"]) is list
            for value in data["tags"]: assert type(value) is str
            question["tags"] = data["tags"]
        questions += [question]
    except:
        return Response('{"error":true}')
    save_questions()
    load_questions()
    return Response('{"error":false}')

@app.route("/listening", methods=["GET", "POST"])
def listening():
    global pending
    data = json.loads(request.data)
    if "challenge" in data:
        return Response(data["challenge"], mimetype='application/json')
    if data["token"] != SLACK_VERIFICATION_TOKEN:
        return make_response("wrong token", 500)
    if data["event"]["type"] == "message":
        threading.Thread(target=message, args=[data["event"]]).start()
    elif data["event"]["type"] == "team_join":
        pending[data["event"]["user"]["id"]] = True
        save_pending()
    return make_response("", 200)

@app.route("/slack/interactive", methods=["POST"])
def interactive():
    data = json.loads(request.form["payload"])
    threading.Thread(target=answer_callback, args=[data]).start()
    return make_response("", 200)


if __name__ == "__main__":
    schedule.every(10).seconds.do(watchdog)
    schedule.run_continuously()
    parse_files()

    app.run(host='0.0.0.0', port=5050)
