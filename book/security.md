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
        return "200 OK", add_entry(session, params)
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
    if "user" in session and 'guest' in params and len(params['guest']) <= 100:
        ENTRIES.append((params['guest'], session["user"]))
    return show_comments(session)
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

``` {.python}
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

``` {.python}
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

Thanks to the same-origin policy and the mitigations for cross-site
scripting, it's now hard for an evil-doer to steal the login token
from our browser. But that doesn't leave us totally safe. Another
concern is our browser misusing the token. One popular exploit of this
type is called *cross-site request forgery*, often shortened to CSRF.

In cross-site request forgery, the attack does not involve the user
going to our guest book site at all. Instead, the user begins on our
evil-doer's website.[^20] That website has a form analogous to the
guest-book form:

``` {.html}
<form action=http://localhost:8000/add method=post>
  <p><input name=guest></p>
  <p><button>Sign the book!</button></p>
</form>
```

Our browser (and a real one) does not care what origin a form is on:
you can submit a form on one origin to another origin, and this
ability is widely used for some reason.[^21] So even if the user fills
out this form on the evil website, the form is still submitted to
the guest-book. When the browser makes that POST request to the
guest-book, it will *also* send along its guest-book cookie. Since the
user has no idea where a form is going---the browser does not show
them that information---they might want to sign a guest book on the
evil-doer's site and end up signing the one on our server
instead.^[And thank goodness we never implemented a change-of-password
form!]

But it gets worse! Suppose the form isn't actually like that, and
instead looks like this:

``` {.html}
<form action=http://localhost:8000/add method=post>
  <p><button>Click me!</button></p>
</form>
```

People will do all sorts of stuff, so they might click that
button.[^you-too] And it may look safe, since there's no `guest` input
area. However, there might be some sneaky JavaScript attached:

[^you-too]: You have clicked similar buttons. Admit it.

``` {.javascript}
form  = document.querySelectorAll('form')[0]
form.addEventListener("submit", function() {
    comment = "Buy from my website: http://evil.doer/";
    input = "<input name=guest value=\"" + comment + "\">";
    form.innerHTML = input;
})
```

This script waits for the user to click the button, and then replaces
the form contents with a `guest` input area with a pre-filled value.
The browser then finds it when it looks for input areas and submits
our hard-coded guest-book entry to the guest-book server. And
remember: the form is submitted by the user's browser, with the user's
cookies, so the post will succeed (if the user is logged in to the
guest book). Posting a comment this way is not too scary (though shady
advertisers will pay for it!) but posting a bank transaction is.

Try it! This should work in both ours and in a real browser. Plus, in a
real browser you could also have a "hidden" input element, which would
mean that you don't need to write any tricky JavaScript at all.

How do we defend against this attack?

We want to make sure that every POST request to `/add` comes from a form
on our website. The normal way to ensure that is to embed a secret
value, called a *nonce*, into the form, and to reject form submissions
that don't come with this secret value.

A nonce is like a login token, but instead of getting it on login, you
get a new one every time you're presented with a form to fill out. In
some sense, it's like a cookie, except that it's stored inside the
HTML and thus lasts for just one request (instead of across many
requests to the same server), so it can't be misused in the same way.

Let's implement nonces in our guest book. Generate a secret nonce and
add it to the form:

``` {.python expected=False}
def show_comments(username):
    # ...
    if username:
        nonce = str(random.random())[2:]
        out += "<form action=add method=post>"
        out +=   "<p><input name=nonce type=hidden value=" + nonce + "></p>"
        # ...
```

The `hidden` input type basically instructs a browser not to render the
input area, but to still submit it in the form. In our browser, which
doesn't support hidden input elements, this will show up as an input
area with a random string of digits---not ideal, but as long as you
don't touch it form submission will work fine.

We'll also need to save the nonce so that we can tell valid from
invalid nonces. I'm going to store that in a `NONCES` variable, which
will store one nonce per user. We'll then check both that the nonce is
valid and also that it is associated with the correct user:[^22]

[^22]: Otherwise an attacker could get a nonce for *their* account and
    then use in a CSRF attack for another user's submission.

``` {.python expected=False}
def show_comments(username):
    # ...
    if username:
        nonce = str(random.random())[2:]
        NONCES[username] = nonce
```

When the form is submitted, we will check the nonce:

``` {.python expected=False}
def add_entry(params, username):
    if not check_nonce(params, username):
        return "Invalid nonce", {}
    # ...

def check_nonce(params, username):
    if 'nonce' not in params: return False
    if username not in NONCES: return False
    return params['nonce'] == NONCES[username]
```

Thanks to this change, in order to add an entry to the guest book, you
need to be logged in and submit the form on the guest book page itself.
And that's a form that we, as the guest book authors, have sole control
over (thanks to our XSS mitigations), so the form submission has now
been secured. Or... I keep saying there's more to security than what's
in this book. Let's just settle for this fact: the guest book is now
more secure than before.

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

[^20]: Why is the user on the attacker's site? Perhaps it has funny
    memes, or it's been hacked and is being used for the attack
    against its will, or perhaps the evil-doer paid for ads on sketchy
    websites where users have low standards for security anyway.

[^21]: For example, search forms that actually just direct you to a
    Google search.

[^23]: Should `microsoft.com` read `google.com`? What about
    `microsoft.co.uk` and `google.co.uk`?

[^24]: Yep, spelled that way.
