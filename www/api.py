#!/usr/bin/python3

import bottle
import json
import os, sys
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

    def typo(self, url, old, new, name):
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
            'name': name,
            'status': 'new',
        })
        self.save()

    def comment(self, url, text, comment, name):
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
            'name': name,
            'status': 'new',
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

@bottle.post("/api/typo")
def typo():
    data = json.load(bottle.request.body)
    DATA.typo(**data)

@bottle.post("/api/comment")
def comment():
    data = json.load(bottle.request.body)
    DATA.comment(**data)

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

if __name__ == "__main__":
    debug = "--debug" in sys.argv
    bottle.run(port=4000, debug=debug, reloader=True)
