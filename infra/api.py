#!/usr/bin/python3

import bottle
import json
import os, sys
import time
import difflib
import html
import hashlib

NOPASSWORD = False

QUIZ_TELEMETRY_FILE = 'quiz_telemetry.json'

bottle.TEMPLATE_PATH.append(".")

class Data:
    def __init__(self, filename):
        self.filename = filename
        if os.path.exists(filename):
            with open(filename, "r") as f:
                self.data = json.load(f)
        else:
            self.data = []

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f)

    def safe_tag(self, tag):
        if tag.lower() in [ "p", "li", "pre", "span" ]:
            return tag
        else:
            return "p"

    def typo(self, url, old, new, name, tag="p"):
        if any(obj['type'] == 'typo' and
               obj['url'] == url and
               obj['old'] == old and
               obj['new'] == new for obj in self.data):
            return
        self.data.append({
            'id': len(self.data),
            'time': time.time(),
            'type': 'typo',
            'tag': self.safe_tag(tag),
            'url': url,
            'old': old,
            'new': new,
            'name': name,
            'status': 'new',
        })
        self.save()

    def text_comment(self, url, text, comment, name, tag="p"):
        if any(obj['type'] == 'comment' and
               obj['url'] == url and
               obj['text'] == text and
               obj['comment'] == comment for obj in self.data):
            return
        self.data.append({
            'id': len(self.data),
            'time': time.time(),
            'type': 'comment',
            'tag': self.safe_tag(tag),
            'url': url,
            'text': text,
            'comment': comment,
            'name': name,
            'status': 'new',
        })
        self.save()

    def chapter_comment(self, url, comment, name, email):
        if any(obj['type'] == 'chapter_comment' and
               obj['url'] == url and
               obj['comment'] == comment for obj in self.data):
            return
        self.data.append({
            'id': len(self.data),
            'time': time.time(),
            'type': 'chapter_comment',
            'url': url,
            'comment': comment,
            'name': name,
            'email': email,
            'status': 'new',
        })
        self.save()

    def status(self, i):
        return self.data[i]["status"]

    def contributors(self):
        return {
            (entry['name'], entry.get('email'))
            for entry in self.data
            if 'name' in entry and 'status' in entry
            if entry["status"] in ["saved", "archived"]
        }

    def set_status(self, i, status):
        if status == "denied-all":
            for d in self.data:
                if d['name'] == self.data[i]['name']:
                    d['status'] = 'denied'
            self.save()
            return
        self.data[i]['status'] = status
        self.save()

    def __iter__(self):
        return iter(self.data)

DATA = Data("db.json")

@bottle.post("/api/typo")
def typo():
    data = json.load(bottle.request.body)
    DATA.typo(**data)

@bottle.post("/api/text_comment")
def text_comment():
    data = json.load(bottle.request.body)
    DATA.text_comment(**data)

@bottle.post("/api/chapter_comment")
def comment():
    data = json.load(bottle.request.body)
    DATA.chapter_comment(**data)

@bottle.post("/api/quiz_telemetry", method=['OPTIONS', 'POST'])
def quiz_telemetry():
    data = json.load(bottle.request.body)
    # Just dump the quiz telemetry into a file for now
    with open(QUIZ_TELEMETRY_FILE, 'a') as fh:
        fh.write(json.dumps(data) + "\n")

def name_key(name):
    parts = name.split()
    if name == "some now-deleted users":
        # This should go last
        return ("ZZZZZZZZZZZZZZ", name.casefold())
    elif len(parts) == 1:
        # Put github usernames last
        return ("ZZZZZZZ", parts[0].casefold())
    else:
        # Very low-effort attempt at "last name"
        return (parts[-1].casefold(), [n.casefold() for n in parts[:-1]])

@bottle.get("/thanks")
@bottle.view("thanks.view")
def thanks():
    author_names = {
        "Pavel Panchekha",
        "Chris Harrelson"
    }

    feedback_names = {name for name, email in DATA.contributors() if name}

    # The list below comes from running
    #
    #   git log --format='%aN' | sort -u`
    #
    # And searching the Github issues and pull requests.
    # List below current as of 14 Mar 2025.
    gh_names = {
        "Abram Himmer",
        "Alex Saveau",
        "Anthony Geoghegan",
        "Ashton Wiersdorf",
        "BO41",
        "Bruno P. Kinoshita",
        "bokken",
        "Daniel Rosenwasser",
        "Ian Briggs",
        "James Wilcox",
        "Jerry Kuch",
        "Jesús Gollonet",
        "Lars Hamann",
        "metamas",
        "Michal Čaplygin",
        "Oliver Byford",
        "Pauline",
        "Pavel Kurochkin",
        "Philip Grabenhorst",
        "Pranav Shridhar",
        "Ryuan Choi",
        "Shinya Fujino",
        "Shuhei Kagawa",
        "Sujal Singh",
        "Thomas Lovett",
        "Xiaochen Zhou",
        "YongWoo Jeon",
    }

    # These should be in order of sponsorship, oldest first.
    # Do not add authors to this.
    patreon_names = [
        "Randy Naar",
        "Min Lee",
        "Zachary Tatlock",
        "Jonas Treub",
        "Alexandru Nedel",
        "Adam Gutglick",
        "Swav Rybak",
        "Rishi Chopra",
        "Yuanhang Xie",
        "Shuhei Kagawa",
        "Vitor Roriz",
        "Maia X.",
        "Parker Henderson",
        "Tiago Pereira",
        "Liza Daly",
        "Sangyeob Han",
        "YongWoo Jeon",
        "Jess",
        "Martin Minkov",
        "Peter Rushforth",
        "Gowtham K",
        "Ryo Ogawa",
        "JaviFML"
    ]

    contributor_names = sorted((feedback_names | gh_names) - author_names, key=name_key) + \
        ["some now-deleted users"]

    return {"patreon": patreon_names, "contribute": contributor_names,}

def splitword(text):
    if not text: return []
    out = [[]]
    ws = text[0].isspace()
    for c in text:
        if c.isspace() == ws:
            out[-1].append(c)
        else:
            out.append([c])
        ws = c.isspace()
    return ["".join(s) for s in out]

def prettify(obj):
    if obj['type'] != 'typo': return obj
    old, new = obj['old'], obj['new']
    old_words = [w + "\n" for w in splitword(old)]
    new_words = [w + "\n" for w in splitword(new)]

    d = difflib.Differ()
    tag = obj.get("tag", "p")
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
    otag = "<ul><li>" if tag == 'li' else ("<" + tag + ">")
    ctag = "</li></ul>" if tag == 'li' else ("</" + tag + ">")
    obj['diff'] = otag + "".join(results) + ctag
    return obj

@bottle.route("/feedback")
@bottle.view("feedback.view")
def feedback():
    new = [prettify(o) for o in DATA if o['status'] == "new"]
    saved = {}
    starred = []
    for o in DATA:
        if o['status'] == "saved":
            page = os.path.split(o['url'])[1].rsplit(".", 1)[0]
            saved.setdefault(page, []).append(prettify(o))
        elif o['status'] == "starred":
            starred.append(prettify(o))

    return { 'new': new, 'saved': saved, 'starred': starred }

@bottle.route("/feedback.rss")
@bottle.view("feedback_rss.view")
def feedback():
    bottle.response.content_type = 'application/rss+xml'
    new = [prettify(o) for o in DATA if o['status'] == "new"]
    return { 'new': new }

@bottle.route("/api/status", method=["POST", "OPTIONS"])
def status():
    data = json.load(bottle.request.body)
    pw = data.get('pw', "")
    heng = hashlib.sha3_256()
    heng.update(pw.encode("utf8"))
    if NOPASSWORD:
        allowed = True
    else:
        with open("pw.hash", "rb") as f:
            good = f.read(256)
        # Equivalent to `good == heng.digest()` but constant-time-ish
        allowed = sum([0 if a == b else 1 for a, b in zip(good, heng.digest())]) == 0

    if allowed:
        DATA.set_status(data['id'], data['status'])
    else:
        raise ValueError("Invalid password")

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
    if len(sys.argv) > 1 and sys.argv[1] == "pw":
        import getpass
        pw = getpass.getpass("Password: ")
        heng = hashlib.sha3_256()
        heng.update(pw.encode("utf8"))
        with open("pw.hash", "wb") as f:
            f.write(heng.digest())
        print("Please run: window.localStorage['pw'] = '" + pw + "'");
    else:
        debug = "--debug" in sys.argv
        NOPASSWORD = "--no-password" in sys.argv
        bottle.run(port=4000, debug=debug, reloader=True)
