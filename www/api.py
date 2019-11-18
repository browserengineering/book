#!/usr/bin/python3

import bottle
import json
import os
import pickle
import time
import difflib
import html

bottle.TEMPLATE_PATH.append(".")

class Data:
    def __init__(self, filename):
        self.filename = filename
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                self.data = pickle.load(f)
        else:
            self.data = []

    def save(self):
        with open(self.filename, "wb") as f:
            pickle.dump(self.data, f)

    def typo(self, url, old, new):
        if any(obj['type'] == 'typo' and
               obj['url'] == url and
               obj['old'] == old and
               obj['new'] == new for obj in self.data):
            return
        self.data.append({
            'id': len(self.data),
            'time': time.time(),
            'type': 'typo',
            'url': url,
            'old': old,
            'new': new,
            'status': 'new'
        })
        self.save()

    def comment(self, url, text, comment):
        if any(obj['type'] == 'comment' and
               obj['url'] == url and
               obj['text'] == text and
               obj['comment'] == comment for obj in self.data):
            return
        self.data.append({
            'id': len(self.data),
            'time': time.time(),
            'type': 'comment',
            'url': url,
            'text': text,
            'comment': comment,
            'status': 'new'
        })
        self.save()

    def status(self, i):
        return self.data[i]["status"]

    def set_status(self, i, status):
        self.data[i]['status'] = status
        self.save()

    def __iter__(self):
        return iter(self.data)

DATA = Data("db.pickle")

@bottle.route("/api/typo", method=["POST", "OPTIONS"])
def typo():
    data = json.load(bottle.request.body)
    DATA.typo(data["url"], data["old"], data["new"])

@bottle.route("/api/comment", method=["POST", "OPTIONS"])
def comment():
    data = json.load(bottle.request.body)
    DATA.comment(data["url"], data["text"], data["comment"])

def prettify(obj):
    if obj['type'] != 'typo': return obj
    old, new = obj['old'], obj['new']
    old_words = [w + "\n" for w in old.split()]
    new_words = [w + "\n" for w in new.split()]

    d = difflib.Differ()
    results = []
    state = " "
    for out in d.compare(old_words, new_words):
        new_state = out[0]
        word = out[2:-1]
        if new_state == "?": continue
        if state != " ":
            results.append("</span>")
        if new_state == "+":
            results.append("<span class='add'>")
        if new_state == "-":
            results.append("<span class='del'>")
        results.append(html.escape(word))
        state = new_state
    if state != " ":
        results.append("</span>")
    obj = obj.copy()
    obj['diff'] = results
    return obj

@bottle.route("/api/feedback")
@bottle.view("feedback.view")
def feedback():
    new = [prettify(o) for o in DATA if o['status'] == "new"]
    saved = [prettify(o) for o in DATA if o['status'] == "saved"]
    return { 'new': new, 'saved': saved }

@bottle.route("/api/status", method=["POST", "OPTIONS"])
def status():
    data = json.load(bottle.request.body)
    DATA.set_status(data['id'], data['status'])

@bottle.route('/<file>')
def static(file):
    return bottle.static_file(file, root=".")

@bottle.route('/')
def index():
    return bottle.static_file("index.html", root=".")

@bottle.route("/auth/tools")
def tools():
    bottle.response.set_cookie("tools", "")
    return "Editing tools enabled"

# For debugging

class EnableCors(object):
    name = 'enable_cors'
    api = 2

    def apply(self, fn, context):
        def _enable_cors(*args, **kwargs):
            # set CORS headers
            bottle.response.headers['Access-Control-Allow-Origin'] = '*'
            bottle.response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
            bottle.response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

            if bottle.request.method != 'OPTIONS':
                # actual request; reply with the actual response
                return fn(*args, **kwargs)

        return _enable_cors

app = bottle.app()
app.install(EnableCors())

if __name__ == "__main__":
    bottle.run(port=8000, debug=True, reloader=True)
