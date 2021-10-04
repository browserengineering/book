---
title: Keeping Data Private
chapter: 10
prev: scripts
next: reflow
...

Our browser has grown up and now runs (small) web applications. With
one final step---user identity via cookies---it can now run all sorts
of personalized online services. But capability demands
responsibility: a browser must secure cookies against adversaries
interested in getting at them. Luckily, browsers have sophisticated
systems for controlling access to cookies and preventing their misuse.

::: {.warning}
Web browser security is a vast topic. It involves securing the web
browser, securing the network, and securing the applications that the
browser runs. It also involves educating the user, so that attackers
can't misleading them into revealing their own secure data. This chapter
can't cover all of that. Instead, it focuses on the mechanisms browsers
have developed to protect the security of web applications. *So*, if
you're writing security-sensitive code, this book is not enough.
:::

Cookies
=======

With what we've implemented so far there's no way for a web server to
tell whether two HTTP requests come from the same user, or
different ones. Our web browser is effectively anonymous.[^1] That
means it can't "log in" anywhere---after logging in, its requests will
look just like those of a new visitor.

[^1]: I don't mean anonymous against malicious attackers, who might
    use *browser fingerprinting* or similar techniques to tell users
    apart. I mean anonymous in the good-faith sense.

The web fixes this problem with cookies. A cookie---the name is
meaningless, ignore it---is a little bit of information stored by your
browser on behalf of a web server. The cookie distinguishes your
browser, and is sent with each web request so the server can
distinguish its users.


Here's how cookies work. In the HTTP response a server can send a
`Set-Cookie` header. This header contains a key-value pair; for
example, the following header sets the value of the `foo` cookie to
`bar`:

    Set-Cookie: foo=bar
    
The browser remembers this key-value pair, and the next time it makes
a request to the same server (cookies are site-specific) it echoes it
back in the `Cookie` header:

    Cookie: foo=bar

Servers can also set multiple cookies and also set parameters like
expiration dates, but this `Set-Cookie` / `Cookie` mechanism is the
core principle.

Servers use cookies to assign identities to their users. For example,
let's write a login system for our guest book. Each user will be
identified by a long random number stored in the `token`
cookie.[^secure-random] The server will either extract a token from
the `Cookie` header, or generate a new one for new visitors:

[^secure-random]: This use of `random.random` returns a decimal number
    with 53 bits of randomness. That's not great; 256 bits is ideal.
    And `random.random` is not a secure random number generator: by
    observing enough tokens you can predict future values and use
    those to hijack accounts. A real web application must use a
    cryptographically secure random number generator for tokens.

``` {.python file=server}
import random

def handle_connection(conx):
    # ...
    if "cookie" in headers:
        token = headers["cookie"][len("token="):]
    else:
        token = str(random.random())[2:]
    # ...
```

Of course, new visitors need to be told to remember their
newly-generated token:

``` {.python file=server}
def handle_connection(conx):
    # ...
    if 'cookie' not in headers:
        response += "Set-Cookie: token={}\r\n".format(token)
    # ...
```

The first code block runs after all the request headers are parsed,
before handling the request in `do_request`, while the the second code
block runs after `do_request` returns, when the server is assembling
the HTTP response.

With these two code changes, each visitor to the guest book now has a
unique identity. We can now use that identities to store information
about each user. Let's do that in a server side `SESSIONS`
variable:[^cookies-limited]

[^cookies-limited]: Browsers and servers both limit header lengths, so
    it's best to store minimal data in cookies. Plus, cookies are sent
    back and forth on every request, so long cookies mean a lot of
    useless traffic.

``` {.python file=server}
SESSIONS = {}

def handle_connection(conx):
    # ...
    session = SESSIONS.setdefault(token, {})
    status, body = do_request(session, method, url, headers, body)
    # ...
```

The user data extracted from the `SESSIONS` object is called the
session data, and I'm passing it to `do_request` so that our request
handlers can read and write user data. Pass that session information
to individual pages like `show_comments` and `add_entry`:

``` {.python file=server}
def do_request(session, method, url, headers, body):
    if method == "GET" and url == "/":
        return "200 OK", show_comments(session)
    # ...
    elif method == "POST" and url == "/add":
        params = form_decode(body)
        add_entry(session, params)
        return "200 OK", show_comments(session)
    # ...
```

You'll also need to modify the argument lists for `add_entry` and
`show_comments`. With the guest book server storing information about
each user accessing the guest book, we can now build a login system.

::: {.further}
The [patent][patent] for cookies says there is "no compelling reason"
for calling them "cookies", but in fact using this term for opaque
identifiers exchanged between programs seems to date way back;
[Wikipedia][wiki-magic-cookie] traces it back to at least 1979, and
cookies were used in [X11][x-cookie] for authentication before they
were used on the web.
:::

[cookie]: https://rpx-patents.s3.amazonaws.com/US/2a377-US7895125B2/US7895125B2.pdf
[wiki-magic-cookie]: https://en.wikipedia.org/wiki/Magic_cookie
[x-cookie]: https://en.wikipedia.org/wiki/X_Window_authorization#Cookie-based_access

A login system
==============

I want users to log in before posting to the guest book. Nothing
complex, just the minimal functionality:

- Users will log in with a username and password.
- The server will hard-code a set of valid logins.
- Users have to be logged in to add guest book entries.
- The server will display who added which guest book entry.

Let's start coding. First, we'll need to store usernames in `ENTRIES`:[^3]

[^3]: The pre-loaded comments reference 1995's *Hackers*. [Hack the
    Planet!](https://xkcd.com/1337)

``` {.python file=server}
ENTRIES = [
    ("No names. We are nameless!", "cerealkiller"),
    ("HACK THE PLANET!!!", "crashoverride"),
]
```

When we print the guest book entries, print the username as well:

``` {.python file=server}
def show_comments(session):
    # ...
    for entry, who in ENTRIES:
        out += '<p>' + entry + " <i>from " + who + '</i></p>'
    # ...
```

Now, we want users to be logged in before posting comments. We'll
determine whether a user is logged in using the `user` key in the
session data:

``` {.python file=server}
def show_comments(session):
    # ...
    if "user" in session:
        out += "<form action=add method=post>"
        out +=   "<p><input name=guest></p>"
        out +=   "<p><button>Sign the book!</button></p>"
        out += "</form>"
    else:
        out += "<a href=/login>Sign in to write in the guest book</a>"
    # ...
```

Likewise, `add_entry` must check that the user is logged in before
posting comments:

``` {.python file=server}
def add_entry(session, params):
    if "user" not in session: return
    # ...
```

Note that the session data (including the `user` key) is stored on the
server, so users can't modify it directly. That's good, because we
only want to set the `user` key if users supply the right password at
the `/login` URL:

``` {.python file=server}
def do_request(session, method, url, headers, body):
    # ...
    elif method == "GET" and url == "/login":
        return "200 OK", login_form(session)
    # ...
```

This URL shows a form with a username and a password field:[^4]

[^4]: I've given the `password` input area the type `password`, which
    in a real browser will draw stars or dots instead of showing what
    you've entered, though our browser doesn't do that.

``` {.python file=server}
def login_form(session):
    body = "<!doctype html>"
    body += "<form action=/ method=post>"
    body += "<p>Username: <input name=username></p>"
    body += "<p>Password: <input name=password type=password></p>"
    body += "<p><button>Log in</button></p>"
    body += "</form>"
    return body 
```

Note that the form `POST`s its data to the `/` URL. We'll want to
route these `POST` requests to a new function that handles logins:

``` {.python file=server}
def do_request(session, method, url, headers, body):
    # ...
    elif method == "POST" and url == "/":
        params = form_decode(body)
        return do_login(session, params)
    # ...
```

This `do_login` function checks passwords and logs people in by
storing their user name in the session data:[^timing-attack]

[^timing-attack]: Actually, using `==` to compare passwords like here
    is a bad idea: Python's equality function for strings scans the
    string from left to right, and exits as soon as it finds a
    difference. So, *how long* it takes to check passwords gives you
    clues about the password; this is called a "[timing side
    channel][timing-attack]". This book is about the browser, not the
    server, but a real web application has to do do a [constant-time
    string comparison][constant-time]!
    
[timing-attack]: https://en.wikipedia.org/wiki/Timing_attack
[constant-time]: https://www.chosenplaintext.ca/articles/beginners-guide-constant-time-cryptography.html

``` {.python file=server}
def do_login(session, params):
    username = params.get("username")
    password = params.get("password")
    if username in LOGINS and LOGINS[username] == password:
        session["user"] = username
        return "200 OK", show_comments(session)
    else:
        out = "<!doctype html>"
        out += "<h1>Invalid password for {}</h1>".format(username)
        return "401 Unauthorized", out
```

Try it out in a normal web browser. You should be able to go to the
main guest book page, click the link to log in, use one of the
username/password pairs above, and post entries.^[The login flow slows
down debugging. You might want to add the empty string as a
username/password pair.] Of course, this login system has a whole slew
of insecurities.[^7] But the focus of this book is the browser, not
the server, so once you're sure it's all working, let's switch gears
and implement cookies inside our own browser.

[^7]: The insecurities include not hashing passwords, not using `bcrypt`, not verifying
    email addresses, not forcing TLS, and not running the server in a sandbox.
    
[bcrypt]: https://auth0.com/blog/hashing-in-action-understanding-bcrypt/


Implementing cookies
====================

Let's implement cookies. To start with, we need a place to store
cookies; that database is traditionally called a *cookie jar*[^2]:

[^2]: Because once you have one silly name it's important to stay
    on-brand.

``` {.python}
COOKIE_JAR = {}
```

Since cookies are site-specific, our cookie jar will map sites to
cookies. Note that the cookie jar is global, not limited to a
particular tab. That means that if you're logged in to a website and
you open a second tab, you're logged in on that tab as well.

When the browser visits a page, it needs to send the cookie for that
site:[^multi-cookies]

[^multi-cookies]: Actually, a site can store multiple cookies at once,
    using different key-value pairs. The browser is supposed to
    separate them with semicolons. I'll leave that for an exercise.

``` {.python replace=(url/(url%2c%20top_level,COOKIE_JAR[host]/cookie}
def request(url, payload=None):
    # ...
    if host in COOKIE_JAR:
        body += "Cookie: {}\r\n".format(COOKIE_JAR[host])
    # ...
```

Symmetrically, receiving the `Set-Cookie` header updates the cookie
jar:[^multiple-set-cookies]

[^multiple-set-cookies]: A server can actually send multiple
    `Set-Cookie` headers to set multiple cookies in one request, and a
    real browser would store all of them.

``` {.python replace=(url/(url%2c%20top_level,=%20kv/=%20(kv%2c%20params),kv/cookie}
def request(url, payload=None):
    # ...
    if "set-cookie" in headers:
        kv = headers["set-cookie"]
        COOKIE_JAR[host] = kv
    # ...
```

You should now be able to use your toy browser to log in to the guest
book and post to it. Moreover, you should be able to open the guest
book in two browsers simultaneously---maybe your toy browser and a
real browser as well---and log in and post as two different users.

Note that `load` calls `request` three times (for the HTML, CSS, and
JS files). Because we handle cookies inside `request`, this should
automatically work correctly, with later requests transmitting cookies
set by previous responses.

Cookies are also accessible from JavaScript's `document.cookie` value.
To implement this, register a `cookie` function:

``` {.python}
class JSContext:
    def __init__(self, tab):
        # ...
        self.interp.export_function("cookie", self.cookie)
        # ...

    def cookie(self):
        _, _, host, _ = self.tab.url.split("/", 3)
        return COOKIE_JAR.get(host, "")
```

Then create the `document.cookie` field in `runtime.js`:

``` {.javascript}
Object.defineProperty(document, 'cookie', {
    get: function() { return call_python("cookie"); }
})
```

Now that our browser supports cookies and uses them for logins, we
need to make sure cookie data is safe from malicious actors. After
all: if someone stole your `token` cookie, they could copy it into
their browser, and the server would think they are you.

Our browser already prevents *other servers* from seeing your cookie
values, because it stores cookies per-host.[^11][^12][^13][^14] But
attackers might be able to get *your server* or *your browser* to help
them steal cookie values...

[^11]: Well... Our connection isn't encrypted, so an attacker could
    pick up the token from there. But another *server* couldn't.

[^12]: Well... Another server could hijack our DNS and redirect our
    hostname to a different IP address, and then steal our cookies. But
    some ISPs support DNSSEC, which prevents that.

[^13]: Well... A state-level attacker could announce fradulent BGP
    routes, which would send even a correctly-retrieved IP address to
    the wrong physical computer.

[^14]: Security is very hard.



Cross-site scripting
====================

With cookies accessible from JavaScript, any scripts run on our server
could, in principle, read the cookie value. This might seem
benign---doesn't our server only run `comment.js`? Well...

A web service needs to defend itself from being *misused*. Consider
the code in our guest book that outputs guest book entries:

``` {.python file=server indent=8}
out += "<p>" + entry + " <i>by " + who + "</i></p>"
```

Note that `entry` can be anything, anything the user might stick into
our comment form. That includes HTML tags, like a custom `<script>`
tag! So, a malicious user could post the comment:

    Hi! <script src="http://my-server/evil.js"></script>

The server would then output the HTML:

    <p>Hi! <script src="http://my-server/evil.js"></script>
    <i> by crashoverride</i></p>

Every user's browser would then download and run the `evil.js` script,
which might read `document.cookie` and send[^how-send] it to the
attacker. The attacker could then impersonate other users, posting as
them or misusing any other capabilities those users had in our
service.

[^how-send]: In a real browser, `evil.js` might use
    [`fetch`][mdn-fetch] to secretly send that cookie to the
    attacker's server, but more complicated attacks work in our
    limited browser as well. For example, the evil script can replace
    the whole page with a link that goes to their site and includes
    the token value in the URL. You've seen "please click to continue"
    screens and have clicked the button unthinkingly; your users will
    too.

[mdn-fetch]: https://developer.mozilla.org/en-US/docs/Web/API/fetch

The core problem here is that user comments are supposed to be data,
but the browser is interpreting them as code. This kind of exploit is
usually called *cross-site scripting* (often written "XSS"), though
misinterpreting data as code is a common security issue in all kinds
of programs.

The standard fix is to encode the data so that it can't be interpreted
as code. For example, in HTML, you can write `&lt;` to display a
less-than sign.[^ch1-ex] Python has an `html` module for this kind of
encoding:

[^ch1-ex]: You may have implemented this as part of an [exercise in
    Chapter 1](http.md#exercises).

``` {.python file=server}
import html

def show_comments(username):
    # ...
    out += "<p>" + html.escape(entry)
    out += " <i>from " + html.escape(who) + "</i></p>"
    # ...
```

This is a good fix, and you should do it. But if you forget to encode
any text anywhere---that's a security bug. So browsers provide
additional layers of defense.

Content security policy
=======================

One such layer is the `Content-Security-Policy` header. The full
specification for this header is quite complex, but in the simplest
case, the header is set to the keyword `default-src` followed by a
space-separated list of servers:

    Content-Security-Policy: default-src http://example.org

This header asks the browser not to load any resources (including CSS,
JavaScript, images, and so on) except from the listed servers. If our
guest book used `Content-Security-Policy`, even an attacker managed to
get a `<script>` added to the page, the browser would refuse to load
and run that script.

Let's implement support for this header. First, we'll need to extract
and parse the `Content-Security-Policy` header:[^more-complex]

[^more-complex]: In reality `Content-Security-Policy` can also list
    scheme-generic URLs and even more complex sources like `'self'`.
    This is a very limited CSP implementation.

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        self.allowed_servers = None
        if "content-security-policy" in headers:
            csp = headers["content-security-policy"].split()
            if len(csp) > 0 and csp[0] == "default-src":
                self.allowed_servers = csp[1:]
        # ...
```

This parsing needs to happen _before_ we request any JavaScript or
CSS, because we now need to check whether those requests are allowed:

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        for script in scripts:
            script_url = resolve_url(script, url)
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue
            # ...
```

Note that we need to first resolve any relative URLs before checking
them against the list of allowed servers. The `allowed_request` check
needs to handle both the case of no `Content-Security-Policy` and the
case where there is one:

``` {.python}
class Tab:
    def allowed_request(self, url):
        if self.allowed_servers == None: return True
        scheme_colon, _, host, _ = url.split("/", 3)
        return scheme_colon + "//" + host in self.allowed_servers
```

The guest book can now send a `Content-Security-Policy` header:

``` {.python file=server}
def handle_connection(conx):
    # ...
    response += "Content-Security-Policy: default-src http://localhost:8000\r\n"
    # ...
```

To check that our implementation works, let's have the guest book
request a script from outside the list of allowed servers:

``` {.python file=server}
def show_comments(session):
    # ...
    out += "<script src=https://example.com/evil.js></script>"
    # ...
```

If you've got everything implemented correctly, the browser should
block the evil script[^evil-js] and report so in the console.

[^evil-js]: Needless to say, `example.com` does not actually host an
    `evil.js` file, and any request to it returns `404 Not Found`.


Cross-site request forgery
==========================

Thanks to `Content-Security-Policy`, web servers can now secure
themselves against cross-site scripting attacks. But that doesn't
leave attackers totally out of luck. While they can no longer convince
web servers to do the wrong things, perhaps they can convince
misdirect our own web browser. One popular exploit of this type is
called *cross-site request forgery*, often shortened to CSRF.

In cross-site request forgery, the attack does not involve the user
going to our guest book site at all. Instead, the user begins on our
evil-doer's website.[^20] That website has a form analogous to the
guest-book form:

[^20]: Why is the user on the attacker's site? Perhaps it has funny
    memes, or it's been hacked and is being used for the attack
    against its will, or perhaps the evil-doer paid for ads on sketchy
    websites where users have low standards for security anyway.

``` {.html}
<form action=http://localhost:8000/add method=post>
  <p><input name=guest></p>
  <p><button>Sign the book!</button></p>
</form>
```

Of course this form is on the evildoer's website, but it *submits* to
our guest book. That means that when you submit the form, the browser
will make an HTTP request to the guest book. And that means it will
send its guest book cookies, and the result is a post to the guest
book. This is bad, because the user has no way of knowing which server
a form submits to---they have no idea they're about to post to an
unrelated service!

Unfortunately, we can't just ban cross-server form submissions.[^21]
And this kind of attack can be further disguised, for example by
hiding the entry widget, pre-filling a post, and styling the button to
look like a normal link. Posting a comment this way is not too scary
(though shady advertisers will pay for it!) but posting a bank
transaction is.^[And thank goodness we never implemented a
change-of-password form!]

[^21]: For example, search forms that actually just direct you to a
    Google search.


How do we defend against this attack?

Well, the usual advice is to make sure that every POST request to
`/add` comes from a form on our website. The way to do that is to
embed a secret value, called a *nonce*, into the form, and to reject
form submissions that don't come with this secret value. Since you can
only get a nonce from the server, and since the nonce is tied to your
user account, the attacker could not embed it in their form and so
could not craft a form for you to submit that the guest book server
would accept.[^like-cookie]

[^like-cookie]: A nonce is somewhat like a cookie, except that it's
stored inside the HTML and thus lasts for just one request (instead of
across many requests to the same server), so it can't be misused in
the same way.

The implementation looks like this. When a form is requested, we
generate a nonce and save it in the user session:[^per-user]

[^per-user]: It's important that nonces are associated with the
    particular user. Otherwise, the attacker can generate a nonce for
    *them* and insert it into a form meant for the *user*.

``` {.python file=server}
def show_comments(session):
    # ...
    if "user" in session:
        nonce = str(random.random())[2:]
        session["nonce"] = nonce
        # ...
        out +=   "<p>Nonce: <input name=nonce value=" + nonce + "></p>"
```

Usually websites actually use `<input type=hidden>`, which is like an
input field but invisible. Our browser doesn't support this, so I'm
using a visible nonce; just don't touch it in the form submission.

Now, when a form is submitted, we check that the nonce is submitted
with it:[^multi-nonce]

[^multi-nonce]: In real websites it's usually best to allow one user
    to have multiple active nonces, so that a user can open two forms
    in two tabs without that overwriting the valid nonce. To prevent
    the nonce set from growing over time, you'd have nonces expire
    after a while. I'm skipping this here, because it's not the focus
    of this chapter.

``` {.python file=server}
def add_entry(session, params):
    if "nonce" not in session or "nonce" not in params: return
    if session["nonce"] != params["nonce"]: return
    # ...
```

Now this form can't be submitted except from our website---and if you
repeat this nonce fix for each form in the web application, it'll be
secure from CSRF attacks. But as with cross-site scripting attacks,
it'd be better for the browser to provide a fail-safe solution that
servers could leverage.

SameSite Cookies
================

For form submissions, that fail-safe solution is `SameSite` cookies.
The idea is that a server can opt into its cookies being `SameSite`,
which means they're not sent on cross-site form
submissions.[^in-progress]

[^in-progress]: At the time of this writing, `SameSite` cookies are
    not standardized, and different browsers handle them differently.
    The [MDN page][mdn-samesite] is helpful for checking the current
    status. Over time, this section may become out of date, though we
    expect the general mechanism of `SameSite` cookies to survive.
    
[mdn-samesite]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite#secure

A cookie is marked `SameSite` in the `Set-Cookie` header like this:

    Set-Cookie: foo=bar; SameSite=Lax

The `SameSite` attribute can take the value `Lax`, `Strict`, or
`None`, and as I write this browsers have and plan different defaults.
Our browser will default to `None` and implement `Lax` as an option.
When `SameSite` is set to `Lax`, the cookie is not sent on cross-site
`POST` requests, but is sent on same-site `POST` or cross-site `GET`
requests.[^iow-links]

[^iow-links]: Cross-site `GET` requests are also known as "clicking a
    link", so you can see why this is a smart set of restrictions. The
    `Strict` version of `SameSite` blocks these too, which can work
    for some websites but not others.
    
To start, let's find a place to store this attribute. I'll modify
`COOKIE_JAR` to store cookie/parameter pairs:

``` {.python replace=(url/(url%2c%20top_level}
def request(url, payload=None):
    if "set-cookie" in headers:
        params = {}
        if ";" in headers["set-cookie"]:
            cookie, rest = headers["set-cookie"].split(";", 1)
            for param_pair in rest:
                name, value = param_pair.split("=", 1)
                params[name.lower()] = value.lower()
        else:
            cookie = headers["set-cookie"]
        COOKIE_JAR[host] = (cookie, params)
```

When sending a cookie in an HTTP request, the browser only sends the
cookie value, not the parameters:

``` {.python replace=(url/(url%2c%20top_level}
def request(url, payload=None):
    if host in COOKIE_JAR:
        cookie, params = COOKIE_JAR[host]
        body += "Cookie: {}\r\n".format(cookie)
```

Now we can reference the `SameSite` parameter of a cookie. But to
actually use it, we need to know which site an HTTP request is being
made from. Let's add a new `top_level` parameter to `request` to track
that:

``` {.python}
def request(url, top_level, payload=None):
    # ...
```

Our browser calls `request` in three places, and we need to send the
top-level URL in each case. At the top of `load`, it makes the initial
request to a page. Modify it like so:

``` {.python}
class Tab:
    def load(self, url, body=None):
        headers, body = request(url, self.url, payload=body)
        # ...
```

Here, `url` is the new URL to visit, but `self.url` is the URL of the
page where the request comes from. Make sure this line comes at the
top of `load`, before `self.url` is set to `url`!

Later, the browser loads styles and scripts with more `request` calls:

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        for script in scripts:
            # ...
            header, body = request(script_url, url)
            # ...
        # ...
        for link in links:
            # ...
            header, body = request(style_url, url)
            # ...
        # ...
```

Note that now the top-level URL is `url`, the new URL we are visiting.
That's because it is the new page that made us request these
particular styles and scripts, so it defines which of those resources
are on the same site.

The `request` function can now check the `top_level` argument before
sending `SameSite` cookies:

``` {.python}
def request(url, top_level, payload=None):
    if host in COOKIE_JAR:
        cookie, params = COOKIE_JAR[host]
        allow_cookie = True
        if params.get("samesite", "none") == "lax":
            _, _, top_level_host, _ = top_level.split("/", 3)
            allow_cookie = (host == top_level_host or method == "GET")
        if allow_cookie:
            body += "Cookie: {}\r\n".format(cookie)
```

Cookies are allowed for all `GET` requests, or if the hosts match---or
if the cookie isn't `SameSite` to begin with. We can now mark our
guest book cookies `SameSite`:

``` {.python file=server}
def handle_connection(conx):
    if 'cookie' not in headers:
        response += "Set-Cookie: token={}; SameSite=Lax\r\n".format(token)
```

This doesn't mean we should remove the nonces we added earlier:
`SameSite` provides a kind of "defense in depth", a fail-safe that
makes sure that even if we forgot a nonce somewhere, we're still
secure against CSRF attacks.

So are we done? Is the guest book totally secure? Uh... no. There's
more---much, *much* more---to web application security than what's in
this book. And just like the rest of this book, there are many other
browser mechanisms that touch on security and privacy. Let's settle
for this fact: the guest book is more secure than before.

::: {.warning}
The purpose of this book is to teach the *internals of web browsers*,
not to teach web application security. There's much more you'd want
to do to make this guest book truly secure, let alone what we'd need
to do to avoid denial of service attacks or to handle spam and
malicious use.
:::

Summary
=======

We've added user data, in the form of cookies, to our browser, and
immediately had to bear the heavy burden of securing that data and
ensuring it was not misused. We then saw the rich browser features we
developed turn into attack vector. And we've made with some simple
tweaks to our guest book to prevent two common web application
vulnerabilities.

Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab10.py
:::

The server is much simpler, but has also grown since last chapter:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/server10.py
:::

Exercises
=========

*Hidden input*: Add support for hidden input elements. Since they
don't need to be laid out, there's no need for a layout type at all!

*Cookie Expiration*: Add support for cookie expiration. Cookie
expiration dates are set in the `Set-Cookie` header, and can be
overwritten if the same cookie is set again with a later date. Save
the same expiration dates in the `TOKENS` variable and use it to
delete old tokens to save memory.

*Cookie Origins*: Add support for cookie origins. Due to the
same-origin policy, a cookie set by `mail.google.com` cannot be read
by, say, `calendar.google.com`, because the host name is the same.
This is a good default,[^23] but is sometimes annoying. A server can
set an `origin` parameter in the `Set-Cookie` header to strip off some
subdomains from the cookie origin. Implement this in your browser,
making sure to send these generalized-origin cookies on any requests
covered by the generalized origin.

*Referer*: When your browser visits a web page, or when it loads a CSS
or JavaScript file, it sends a `Referer` header[^24] containing the
URL it is coming from. Sites often use this for analytics. Implement
this in your browser. However, some URLs contain personal data that
they don't want revealed to other websites, so browsers support a
`Referer-Policy` header, which can contain values like `no-referer`
(never send the `Referer` header when leaving this page) or
`same-origin` (only do so if navigating to another page on the same
origin). Implement those two values for `Referer-Policy`.

[^23]: Should `microsoft.com` read `google.com`? What about
    `microsoft.co.uk` and `google.co.uk`?

[^24]: Yep, spelled that way.
