---
title: Downloading Web Pages
chapter: 1
prev: history
next: graphics
...

Web ブラウザは URL で識別される情報を表示します。最初のステップは、その URL を使用してインターネット上のどこかにあるサーバーに接続し、情報をダウンロードすることです。

サーバーへの接続
======================

インターネットの閲覧はURLから始まります。[^url] ブラウザがアクセスする特定の Web ページを識別する短い文字列。

[^url]: 「URL」は「Uniform Resource Locator」の略で、Web ページ (リソース) を識別するポータブル (統一) な方法であり、それらのファイルにアクセスする方法 (ロケーター) を記述するものであることを意味します。

::: {.cmd .web-only .center html=True}
    python3 infra/annotate_code.py <<EOF
    [http][tl|Scheme]://[example.org][bl|Hostname][/index.html][tl|Path]
    EOF
:::

::: {.center .web-only}
Figure 1: The syntax of URLs.
:::

::: {.print-only}
![図 1: URL の構文。](im/http-url.png)
:::

URL には 3 つの部分があります (図 1 を参照)。スキームは 情報を取得する 方法、ホスト名は情報の取得場所、パスは取得する情報について説明します。URL にはポート、クエリ、フラグメントなどのオプションの部分もありますが、これについては後で説明します。

URLから、ブラウザはウェブページのダウンロードプロセスを開始できます。ブラウザはまず、ローカルオペレーティングシステム（OS）にホスト名で記述されたサーバーに接続するように要求します。次にOSはドメインネームシステム（DNS）サーバーと通信し、DNSサーバーはURLを変換します。のようなホスト名を、のような宛先 IP アドレスexample.orgに変換します 。93.184.216.34現在、IP (インターネット プロトコル) には IPv4 と IPv6 の 2 つのバージョンがあります。IPv6 アドレスははるかに長く、通常は 16 進数で記述されますが、それ以外は違いは重要ではありません。次に、OS はルーティング テーブルと呼ばれるものを使用して、その宛先 IP アドレスとの通信に最適なハードウェア (ワイヤレスまたは有線など) を決定し、デバイス ドライバーを使用して信号を有線または無線で送信します。ここでは手順を省略します。有線では、まず通信をイーサネット フレームでラップする必要がありますが、無線ではさらに多くのことを行う必要があります。簡潔に説明します。これらの信号は一連のルーターによって受信され送信されるあるいはスイッチやアクセス ポイントなど、さまざまな可能性がありますが、最終的にはルーターになります。それぞれが最適な方向を選択してメッセージを送信し、最終的に宛先にメッセージが届くようにします。また、返信を転送できるように、メッセージの送信元を記録することもあります。メッセージがサーバーに到達すると、接続が作成されます。とにかく、ここでのポイントは、ブラウザが OS に「 に接続させてください example.org」と伝え、実際に接続が確立されることです。

多くのシステムでは、次のようにプログラムを使用してこの種の接続を設定できます telnet。

[^dns]: nslookup.ioなどの DNS ルックアップ ツールやdigコマンドを使用して、この変換を自分で実行できます。

[^ipv6]: 現在、IP (インターネット プロトコル) には IPv4 と IPv6 の 2 つのバージョンがあります。IPv6 アドレスははるかに長く、通常は 16 進数で記述されますが、それ以外は違いは重要ではありません。

[^skipped-steps]: こでは手順を省略します。有線では、まず通信をイーサネット フレームでラップする必要がありますが、無線ではさらに多くのことを行う必要があります。簡潔に説明します。

[^switch-ap]: あるいはスイッチやアクセス ポイントなど、さまざまな可能性がありますが、最終的にはルーターになります。

[^network-tracing]: また、返信を転送できるように、メッセージの送信元を記録することもあります。

多くのシステムでは、次のようにプログラムを使用してこの種の接続を設定できます telnet。

``` {.example}
telnet example.org 80
```

::: {.web-only}
(注: 灰色のアウトラインが表示されている場合、問題のコードは単なる例であり、実際にはブラウザのコードの一部ではないことを意味します。)
:::

::: {.print-only}
(Note: When you see a black frame, it means that the code in question is
an example only, and *not* actually part of our browser's code.)
:::

::: {.installation}
をインストールする必要がある場合がありますtelnet。これは、デフォルトでは無効になっていることが多いです。Windows では、コントロール パネルの[プログラムと機能] / [Windows の機能の有効化または無効化] に移動しますnc -v。再起動する必要があります。これを実行すると、何かを印刷する代わりに画面がクリアされますが、それ以外は通常どおり動作します。macOS では、の代わりに コマンド を使用できますtelnet。

``` {.example}
nc -v example.org 80
```

出力は少し異なりますが、動作は同じです。ほとんどの Linux システムでは、パッケージ マネージャー (通常は および というパッケージ) から またはtelnetを インストールできます。nctelnetnetcat
:::

次のような出力が得られます。

``` {.output}
Trying 93.184.216.34...
Connected to example.org.
Escape character is '^]'.
```

これは、OS がホスト名 example.orgを IP アドレスに変換し93.184.216.34 、接続できたことを意味します。エスケープ文字に関する行は、わかりにくいtelnet機能を使用するための指示にすぎません。と話すことができるようになりましたexample.org。

[^10]: エスケープ文字に関する行は、わかりにくいtelnet機能を使用するための指示にすぎません。

::: {.further}
URL 構文はRFC 3986で定義されています。その第一著者は Tim Berners-Lee です。驚くことではありません。第二著者は Roy Fielding です。彼は HTTP 設計の主要な貢献者であり、博士論文で Web の Representational State Transfer (REST) アーキテクチャを説明したことでも有名です。この論文では、REST によって Web が分散型で成長できるようになった理由が説明されています。今日では、多くのサービスがこれらの原則に従った「RESTful API」を提供していますが、それについては多少の混乱があるようです 。
:::

[rest-thesis]: https://ics.uci.edu/~fielding/pubs/dissertation/fielding_dissertation_2up.pdf
[what-is-rest]: https://twobithistory.org/2020/06/28/rest.html

情報の要求
======================

接続されると、ブラウザはパスを指定してサーバーに情報を要求します。パスは、 のようにホスト名の後に続く URL の一部です/index.html。要求の構造を図 2 に示します。これを に入力してtelnet試してください。

::: {.cmd .web-only html=True}
    python3 infra/annotate_code.py <<EOF
    [GET][tl|Method] [/index.html][tr|Path] [HTTP/1.0][tl|HTTP Version]
    [Host][bl|Header]: [example.org][bl|Value]

    EOF
:::

::: {.center .web-only}
Figure 2: An annotated HTTP GET request.
:::

::: {.print-only}
![Figure 2: An annotated HTTP GET request.](im/http-get.png)
:::

ここでの単語はGETブラウザが情報を受け取りたいという意味です。情報を送信する意図があるかどうかはわかりますPOSTが、他にももっとわかりにくいオプションがいくつかあります。次にパスが続き、最後にブラウザがHTTPHTTP/1.0バージョン 1.0 を使っていることをホストに伝える単語があります。HTTP には複数のバージョンがあります ( 0.9、1.0、1.1、2.0、3.0 )。HTTP 1.1 標準では、キープアライブなどのさまざまな便利な機能が追加されていますが、簡潔さを優先するため、ブラウザではそれらを使用しません。また、HTTP 2.0 も実装していません。HTTP 2.0 は 1.xシリーズよりもはるかに複雑で、大規模で複雑な Web アプリケーションを対象としていますが、ブラウザでは実行できません

[HTTP]: https://developer.mozilla.org/en-US/docs/Web/HTTP

最初の行の後、各行にはヘッダーが含まれ、ヘッダーには名前 ( などHost) と値 ( など example.org) が含まれます。異なるヘッダーはそれぞれ異なる意味を持ちます。 Hostたとえば、ヘッダーはサーバーに、それが誰であるかを伝えます。これは、同じ IP アドレスが複数のホスト名に対応し、複数の Web サイトをホストしている場合 ( およびexample.comなど example.org) に便利です。Hostヘッダーは、複数の Web サイトのうちどれが必要かをサーバーに伝えます。基本的に、これらの Web サイトはHost適切に機能するためにヘッダーを必要とします。1 台のコンピューターで複数のドメインをホストすることは非常に一般的です。送信できるヘッダーは他にもたくさんありますが、 Host今のところはこれだけにしておきましょう。

最後に、ヘッダーの後に 1 行の空白行が続きます。これは、ヘッダーの処理が完了したことをホストに通知します。したがって、 に空白行を入力すると telnet(リクエストの 2 行を入力した後に Enter キーを 2 回押す)、 から応答が返されるはずです example.org。

[^11]: 情報を送信する意図があるかどうかはわかりますPOSTが、他にももっとわかりにくいオプションがいくつかあります。

[^13]: これは、同じ IP アドレスが複数のホスト名に対応し、複数の Web サイトをホストしている場合 ( およびexample.comなど example.org) に便利です。Hostヘッダーは、複数の Web サイトのうちどれが必要かをサーバーに伝えます。基本的に、これらの Web サイトはHost適切に機能するためにヘッダーを必要とします。1 台のコンピューターで複数のドメインをホストすることは非常に一般的です。


::: {.further}
HTTP/1.0 はRFC 1945で標準化され、HTTP/1.1 は RFC 2616で標準化されています。HTTP は理解と実装が簡単なように設計されており、あらゆる種類のコンピューターで簡単に導入できます。 に直接 HTTP と入力できるのは偶然ではありません。また、HTTP が電子メールの Simple Mail Transfer Protocol ( SMTPtelnet )と同様に、プレーンテキストと改行を使用する「行ベースのプロトコル」であることも偶然ではありません。結局のところ、このパターン全体は、初期のコンピューターが行ベースのテキスト入力しかできなかったことに由来しています。実際、最初の 2 つのブラウザーのうちの 1 つには行モードの UIがありました。
:::

[SMTP]: https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol
[line-mode]: https://en.wikipedia.org/wiki/Line_Mode_Browser

サーバーの応答
=====================

The server's response starts with the line in Figure 3.

::: {.cmd .web-only html=True}
    python3 infra/annotate_code.py <<EOF
    [HTTP/1.0][tr|HTTP Version] [200][bl|Response Code] [OK][tl|Response Description]
    EOF
:::

::: {.center .web-only}
Figure 3: Annotated first line of an HTTP response.
:::

::: {.print-only}
![Figure 3: Annotated first line of an HTTP response.](im/http-status.png)
:::

これは、ホストが を話すことを確認し HTTP/1.0、リクエストが「OK」(数値コードは 200) であることを確認したことを示しています。 についてはご存知かもしれませんが 、これはや404 Not Foundと同様に、別の数値コードと応答です。このようなコードはたくさんあり、非常にすっきりとした構成になっています。403 Forbidden500 Server Error

 - 100 番台は情報メッセージです。
 - 200 は成功したことを意味します。
 - 300 番台はフォローアップアクション (通常はリダイレクト) を要求します。
 - 400 番台は不正なリクエストを送信したことを意味します。
 - 500 番台はサーバーがリクエストを適切に処理しなかったことを意味します。

サーバーとブラウザのどちらに問題があるかを示す 2 セットのエラー コード (400 番台と 500 番台) があるという優れた点に注目してください。もっと正確に言えば、サーバーが誰が悪いと考えているかです。さまざまなコードの完全なリストはWikipedia で見つかります。また、新しいコードが随時追加されています。

この200 OK行の後に、サーバーは独自のヘッダーを送信します。私がこれを実行したとき、次のヘッダーが返されました (ただし、実際のヘッダーは異なります)。

``` {.example}
Age: 545933
Cache-Control: max-age=604800
Content-Type: text/html; charset=UTF-8
Date: Mon, 25 Feb 2019 16:49:28 GMT
Etag: "1541025663+gzip+ident"
Expires: Mon, 04 Mar 2019 16:49:28 GMT
Last-Modified: Fri, 09 Aug 2013 23:54:35 GMT
Server: ECS (sec/96EC)
Vary: Accept-Encoding
X-Cache: HIT
Content-Length: 1270
Connection: close
```

ここには、要求している情報 ( 、、 )、サーバー ( 、 )、ブラウザーがこの情報をキャッシュする期間 ( 、、 )、その他さまざまなことに関する多くの情報があります。とりあえず先に進みましょう。Content-TypeContent-LengthLast-ModifiedServerX-CacheCache-ControlExpiresEtag

ヘッダーの後に空白行があり、その後にHTMLコードが続きます。これはサーバーの応答の本文Content-Typeと呼ばれ、ブラウザーは ヘッダーに HTML であると記載されているため、それが HTML であることを認識しますtext/html。この HTML コードには、Web ページ自体のコンテンツが含まれています。

HTTP 要求/応答トランザクションは、図 4 にまとめられています。ここで、手動接続から Python への切り替えを行いましょう。

::: {.center}
![図 4: HTTP リクエストとレスポンスのペアは、Web ブラウザが Web サーバーから Web ページを取得する方法です。](im/http-request-2.gif)
:::

::: {.further}
Wikipedia には、HTTPヘッダー と応答コードの優れたリストがあります。HTTP 応答コードの中には、 402 「支払いが必要」のようにほとんど使用されないものもあります。このコードは、「デジタル キャッシュまたは (マイクロ) 支払いシステム」で使用することを意図していました。電子商取引は応答コード 402 がなくても健在ですが、マイクロ支払いは(まだ?) あまり普及していません。多くの人 (私も含めて!) が良いアイデアだと考えているにもかかわらずです。
:::

[headers]: https://en.wikipedia.org/wiki/List_of_HTTP_header_fields

[codes]: https://en.wikipedia.org/wiki/List_of_HTTP_status_codes

[402]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/402

[micropayments]: https://en.wikipedia.org/wiki/Micropayment

PythonにおけるTelnet
================

これまでは を使用して別のコンピュータと通信してきました telnet。しかし、これは非常に単純なプログラムであり、プログラムで同じことを行うことができます。URL からホスト名とパスを抽出し、ソケットを作成し、リクエストを送信して、応答を受信するtelnet必要があります 。Python には URL を解析するためのライブラリがありますurllib.parseが、独自に実装すると学習に役立つと思います。また、この本は Python に特化したものではなくなります。

URL の解析から始めましょう。URL を解析するとオブジェクトが返されるようにしURL、解析コードをコンストラクターに配置します。

[^why-not-parse]: Python には URL を解析するためのライブラリがありますurllib.parseが、独自に実装すると学習に役立つと思います。また、この本は Python に特化したものではなくなります。


``` {.python}
class URL:
    def __init__(self, url):
        # ...
```

メソッド__init__は、クラス コンストラクター用の Python 特有の構文であり、self常にメソッドの最初のパラメーターにする必要があるパラメーターは、 thisC++ または Java の Python 版です。

まずは、 によって URL の残りの部分から区切られている スキーム から始めましょう://。ブラウザは のみをサポートしているhttpので、これも確認しましょう。

``` {.python replace=%3d%3d/in,%22http%22/[%22http%22%2c%20%22https%22]}
class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme == "http"
```

ここで、ホストとパスを分離する必要があります。ホストは最初の の前に来ます/が、パスはそのスラッシュとその後のすべてです。

``` {.python}
class URL:
    def __init__(self, url):
        # ...
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url
```

(この例のように を含むコード ブロックがある場合は# ...、既存のメソッドまたはブロックにコードを追加していることを意味します。) split(s, n)メソッドは、 の最初の nコピーで文字列を分割しますs。ホスト名とパスの間のスラッシュを処理するための巧妙なロジックがここにあることに注意してください。その (オプションの) スラッシュはパスの一部です。

におよび フィールドURLが追加されたので、その URL の Web ページをダウンロードできます。これを新しいメソッドで実行します。hostpathrequest

``` {.python}
class URL:
    def request(self):
        # ...
```

Python では、メソッドのパラメータを常に記述する必要があることに注意してくださいself。今後は、メソッドの定義をそれほど重要視しなくなるでしょう。メソッドまたは関数内にまだ存在しないコードを含むコード ブロックが表示された場合は、それを定義していることを意味します。

Web ページをダウンロードする最初のステップは、ホストに接続することです。オペレーティング システムには、このために「ソケット」と呼ばれる機能が用意されています。他のコンピューターと通信する場合 (何かを伝えるため、または何かを伝えるのを待つため)、ソケットを作成します。その後、そのソケットを使用して情報を送受信できます。他のコンピューターと通信する方法は複数あるため、ソケットにはいくつかの種類があります

-   ソケットにはアドレス ファミリがあり、これによって他のコンピュータを見つける方法がわかります。アドレス ファミリの名前は で始まります AF。 が必要ですAF_INETが、たとえば は AF_BLUETOOTH別の例です。
-   ソケットには、発生する会話の種類を表す タイプSOCKがあります。タイプの名前は で始まります。 が必要ですSOCK_STREAM。これは、各コンピューターが任意の量のデータを送信できることを意味しますが、 もあります SOCK_DGRAM。この場合は、コンピューターが互いに固定サイズのパケットを送信します。
-   ソケットには、2 台のコンピュータが接続を確立する手順を記述するプロトコルIPPROTO_TCPがあります。プロトコルの名前はアドレス ファミリによって異なりますが、ここでは を使用します。

[^dgram]: DGRAM「データグラム」の略で、ポストカードのようなものをイメージしています。

[^quic]: 新しいバージョンの HTTP では、伝送制御プロトコル (TCP) の代わりにQUICと呼ばれるものが使用されます が、ブラウザは HTTP 1.0 を使用します。


これらすべてのオプションを選択すると、次のようなソケットを作成できます。

[^sockets]: このコードは Pythonsocketライブラリを使用していますが、お気に入りの言語には非常によく似たライブラリが含まれている可能性があります。API は基本的に標準化されています。Python では、渡すフラグはデフォルトなので、実際に を呼び出すことができます socket.socket()。別の言語でこの手順に従う場合に備えて、ここではフラグを残しておきます。

``` {.python}
import socket

class URL:
    def request(self):
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
```

ソケットを取得したら、他のコンピュータに接続するように指示する必要があります。そのためには、ホストとポートが必要です。ポートは使用しているプロトコルによって異なりますが、現時点では 80 である必要があります。

``` {.python replace=80/self.port}
class URL:
    def request(self):
        # ...
        s.connect((self.host, 80))
```

これは、example.org接続を設定し、両方のコンピューターがデータを交換できるように準備するために行われます。

::: {.quirk}
当然ながら、オフラインの場合はこの方法は機能しません。また、プロキシの背後にいる場合や、さまざまなより複雑なネットワーク環境にいる場合も機能しない可能性があります。回避策は設定によって異なります。プロキシを無効にするだけの簡単なものもあれば、もっと複雑なものもあります。
:::

呼び出しには 2 つの括弧があることに注意してくださいconnect。 connectは 1 つの引数を取り、その引数はホストとポートのペアです。 これは、アドレス ファミリによって引数の数が異なるためです。

::: {.further}
Python が多かれ少なかれ直接実装している「ソケット」 API は、1983 年の 4.2 BSD Unix 用のオリジナルの「バークレー ソケット」 API 設計から派生したものです。もちろん、Windows と Linux は単に API を再実装しただけですが、macOS と iOS は実際には依然としてBSD Unix から派生した大量のコードを使用しています。
:::

[bsd-sockets]: https://en.wikipedia.org/wiki/Berkeley_sockets

[mac-bsd]: https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/KernelProgramming/BSD/BSD.html

Request and Response
====================

接続が確立されたので、他のサーバーにリクエストを送信します。そのためには、次のsendメソッドを使用してデータを送信します。

``` {.python}
class URL:
    def request(self):
        # ...
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        request += "\r\n"
        s.send(request.encode("utf8"))
```
このsendメソッドは、リクエストをサーバーに送信するだけです。send 実際には数値を返します47。この場合は です。これは、他のコンピュータに送信したデータのバイト数を示します。たとえば、データ送信の途中でネットワーク接続が失敗した場合、接続が失敗する前に送信したデータ量を知る必要がある場合があります。このコードには、正確に記述しなければならない点がいくつかあります。まず、改行には の\r\n 代わりにを使用することが非常に重要です。また、最後に2 つの\n改行を入れて、リクエストの最後に空白行を送信することも重要です。これを忘れると、他のコンピュータは改行の送信を待ち続け、あなたもその応答を待ち続けることになります。 \r\nコンピューターは限りなく文字通りに解釈します。

また、encode呼び出しにも注意してください。データを送信するときは、生のビットとバイトを送信していることを覚えておくことが重要です。これらはテキスト、画像、またはビデオを形成する可能性があります。ただし、Python 文字列はテキストを表すために特別に使用されます。encodeメソッドはテキストをバイトに変換しますが、 decode逆方向の対応するメソッドがあります。呼び出すときに encode、どの文字エンコードを使用するかをdecodeコンピューターに伝える必要があります。これは複雑なトピックです。ここでは一般的な文字エンコードを使用しており、多くのページで機能しますが、実際の使用ではより注意する必要があります。utf8Python では、テキストとバイトに異なる型を与えることで注意を促すようにしています。

[^send-return]: send 実際には数値を返します47。この場合は です。これは、他のコンピュータに送信したデータのバイト数を示します。たとえば、データ送信の途中でネットワーク接続が失敗した場合、接続が失敗する前に送信したデータ量を知る必要がある場合があります。

[^literal]: コンピューターは限りなく文字通りに解釈します。


[^charset]: 呼び出すときに encode、どの文字エンコードを使用するかをdecodeコンピューターに伝える必要があります。これは複雑なトピックです。ここでは一般的な文字エンコードを使用しており、多くのページで機能しますが、実際の使用ではより注意する必要があります。utf8

``` {.python .output}
>>> type("text")
<class 'str'>
>>> type("text".encode("utf8"))
<class 'bytes'>
```
strversusに関するエラーが表示される場合は、どこかでまたは bytesを呼び出すのを忘れたためです。encodedecode

サーバーの応答を読み取るには、ソケットの関数を使用します。この関数は、すでに到着している応答のビットを返します。次に、到着したビットを収集するループを記述します。ただし、Python では、ループを非表示にするヘルパー関数read を使用できます。makefile

[^socket-loop]: If you're in another language, you might only have `socket.read`
available. You'll need to write the loop, checking the socket status,
yourself.


``` {.python}
class URL:
    def request(self):
        # ...
        response = s.makefile("r", encoding="utf8", newline="\r\n")
```

ここで、 は、makefileサーバーから受信したすべてのバイトを含むファイルのようなオブジェクトを返します。utf8 エンコーディング、つまりバイトを文字に関連付ける方法を使用して、それらのバイトを文字列に変換するように Python に指示しています。ハードコーディングはutf8 正しくありませんが、ほとんどの英語の Web サイトで問題なく機能するショートカットです。実際、Content-Typeヘッダーには通常、charset本文のエンコードを指定する宣言が含まれています。この宣言がない場合、ブラウザーは をデフォルトにせず utf8、文字の頻度に基づいて推測します。推測が間違っていると、見苦しい奇妙な áççêñ£ß が表示されます。また、HTTP の奇妙な行末についても Python に通知しています。

応答を分割してみましょう。最初の行はステータス行です。

[^utf8]: ハードコーディングはutf8 正しくありませんが、ほとんどの英語の Web サイトで問題なく機能するショートカットです。実際、Content-Typeヘッダーには通常、charset本文のエンコードを指定する宣言が含まれています。この宣言がない場合、ブラウザーは をデフォルトにせず utf8、文字の頻度に基づいて推測します。推測が間違っていると、見苦しい奇妙な áççêñ£ß が表示されます。


応答を分割してみましょう。最初の行はステータス行です。
^[ブラウザがサポートする唯一のコードである 200 が必須であると断言することもできましたが、サーバーはエラー コードに対しても、一般的には役立つ、ユーザーが判読できる HTML エラー ページを出力するため、返された本文をブラウザにレンダリングさせる方が適切です。これは、Web を段階的に簡単に実装できるもう 1 つの方法です]


``` {.python}
class URL:
    def request(self):
        # ...
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
```

サーバーの HTTP バージョンが自分のものと同じかどうかはチェックしていないことに注意してください。これは良い考えのように思えるかもしれませんが、HTTP 1.0 で通信しているにもかかわらず HTTP 1.1 で応答する、誤って構成されたサーバーが多数存在します。幸いなことに、プロトコルは混乱を起こさない程度に似ています。

ステータス ラインの後にヘッダーが続きます。

``` {.python}
class URL:
    def request(self):
        # ...
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
```

ヘッダーについては、各行を最初のコロンで分割し、ヘッダー名とヘッダー値のマップを入力します。ヘッダーは大文字と小文字を区別しないため、小文字に正規化します。より多くの言語でより適切に機能するため、casefold の代わりにを使用しました。lowerまた、HTTP ヘッダー値では空白は重要ではないため、先頭と末尾の余分な空白を削除します。

ヘッダーにはあらゆる種類の情報を記述できますが、アクセスしようとしているデータが通常とは異なる方法で送信されていることを示すヘッダーがいくつかあるため、特に重要です。これらのヘッダーが存在しないことを確認しましょう。

[^casefold]: より多くの言語でより適切に機能するため、casefold の代わりにを使用しました。lower

[casefold]: https://docs.python.org/3/library/stdtypes.html#str.casefold

[^if-te]: 演習 1-9 では、これらのヘッダーが存在する場合にブラウザーがどのように処理するかについて説明します。

``` {.python}
class URL:
    def request(self):
        # ...
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
```

送信されたデータを取得する通常の方法は、ヘッダーの後のすべてです。

``` {.python}
class URL:
    def request(self):
        # ...
        content = response.read()
        s.close()
```

表示するのはこの本体なので、それを返しましょう:

``` {.python}
class URL:
    def request(self):
        # ...
        return content
```

それでは、実際にレスポンス本文にテキストを表示してみましょう。

::: {.further}
ヘッダーContent-Encoding により、サーバーは Web ページを送信する前に圧縮できます。テキストの多い大きな Web ページは圧縮率が高く、その結果、ページの読み込みが速くなります。ブラウザーは、サポートしている圧縮アルゴリズムをリストするために、リクエストでAccept-Encoding ヘッダーTransfer-Encodingを送信する必要があります。 も同様で、データを「チャンク化」することもできます。多くのサーバーは、これを圧縮と一緒に使用しているようです。
:::

[ce-header]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Encoding
[te-header]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Transfer-Encoding
[ae-header]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Encoding

HTMLの表示
===================

レスポンス本文の HTML コードは、 にアクセスしたときにブラウザ ウィンドウに表示されるコンテンツを定義します http://example.org/index.html。今後の章で HTML についてさらに詳しく説明しますが、今はごく簡単に説明します。

HTML には、タグとテキストがあります。各タグは で始まり<で終わります>。一般的に、タグはコンテンツがどのようなものかを示し、テキストは実際のコンテンツです。ただし、 などの一部のタグはimgコンテンツであり、それに関する情報ではありません。ほとんどのタグは、開始タグと終了タグのペアになっています。たとえば、ページのタイトルは、<title>と のタグのペアで囲まれています</title>。山括弧内の各タグには、タグ名 (titleこの例のように) があり、その後にオプションでスペースが 1 つ入り、その後に属性が続きます。タグのペアには、 の/ 後にタグ名が続きます (属性はありません)。

そこで、非常にシンプルな Web ブラウザーを作成するには、ページの HTML を取得し、その中のタグを除くすべてのテキストを印刷してみましょう。SyntaxErrorこの例で Python が最後の行を指すを生成する場合end 、Python 3 ではなく Python 2 を実行していることが原因である可能性があります。Python 3 を使用していることを確認してください。これを新しい関数で実行しますshow。

[^content-tag]: ただし、 などの一部のタグはimgコンテンツであり、それに関する情報ではありません。

[^python2]: SyntaxErrorこの例で Python が最後の行を指すを生成する場合end 、Python 3 ではなく Python 2 を実行していることが原因である可能性があります。Python 3 を使用していることを確認してください。


``` {.python}
def show(body):
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")
```

このコードはかなり複雑です。リクエスト ボディを 1 文字ずつ処理し、2 つの状態 (in_tag現在山括弧のペアの間にある場合 、および ) がありますnot in_tag。現在の文字が山括弧の場合、これらの状態が切り替わり、タグ内ではない通常の文字が印刷されます。この end引数は、文字の後に改行を印刷しないように Python に指示します。

requestとを連結するだけで Web ページを読み込むことができるようになりました show。

[^python-newline]: この end引数は、文字の後に改行を印刷しないように Python に指示します。


``` {.python}
def load(url):
    body = url.request()
    show(body)
```

loadコマンドラインから実行するには、次のコードを追加します。

``` {.python}
if __name__ == "__main__":
    import sys
    load(URL(sys.argv[1]))
```

最初の行は Python バージョンの関数でmain、このスクリプトをコマンドラインから実行する場合にのみ実行されます。コードはコマンドラインから最初の引数 ( sys.argv[1]) を読み取り、それを URL として使用します。次のコードを URL で実行してみてください http://example.org/。



``` {.sh}
python3 browser.py http://example.org/
```

公式サンプル Web ページへようこそという短いテキストが表示されます。この章でもそれを使用してみることができます。

::: {.further}
HTML は、URL や HTTP と同様に、基本的なレベルで解析および表示が非常に簡単になるように設計されています。また、当初は HTML の機能が非常に少なかったため、ここで紹介したものよりそれほど凝ったものではなく、コンテンツを使いやすい形で表示できるコードを作成することができました。当社の非常にシンプルで基本的な HTML パーサーでも、browser.engineering Web サイトのテキストを印刷できます。
:::

暗号化された接続
=====================

今のところ、ブラウザはこのhttpスキームをサポートしています。これはかなり一般的なスキームです。しかし、ますます多くの Web サイトがこの httpsスキームに移行しており、多くの Web サイトがこれを必須としています。

との違いは、httpの方がより安全であるhttpsということですhttpsが、もう少し具体的に説明しましょう。httpsスキーム、またはより正式には HTTP over TLS (Transport Layer Security) は、ブラウザーとホスト間のすべての通信が暗号化されることを除いて、通常のhttp スキームと同じです。 この仕組みには、どの暗号化アルゴリズムが使用されるか、共通の暗号化キーがどのように合意されるか、そしてもちろん、ブラウザーが正しいホストに接続していることを確認する方法など、かなり多くの詳細があります。 関連するプロトコル レイヤーの違いは、図 5 に示されています。

::: {.center}
![図 5: HTTP と HTTPS の違いは、TLS レイヤーが追加されていることです。](im/http-tls-2.gif)
:::

幸いなことに、Pythonsslライブラリはこれらすべての詳細を実装しているので、暗号化された接続は通常の接続とほぼ同じくらい簡単です。この使いやすさは、状況によっては不適切となる可能性のあるいくつかのデフォルト設定を受け入れることで実現されますが、教育目的であれば問題ありません。

との暗号化された接続はssl非常に簡単です。 ソケット をすでに作成しs、 に接続しているとしますexample.org。接続を暗号化するには、 を使用して コンテキストssl.create_default_contextを作成し、そのコンテキストを使用してソケット をラップします。 ctxs

``` {.python .example}
import ssl
ctx = ssl.create_default_context()
s = ctx.wrap_socket(s, server_hostname=host)
```

はwrap_socket新しいソケットを返し、それをs変数に保存し直します。これは、元のソケット経由でデータを送信したくないためです。暗号化されず、混乱を招く恐れがあります。server_hostname引数は、正しいサーバーに接続しているかどうかを確認するために使用されます。ヘッダーと一致する必要があります Host。

::: {.installation}
macOS では、ほとんどの Web サイトで Python のパッケージを使用する前に、 「証明書のインストール」というプログラムを実行する必要があります。ssl
:::

[macos-fix]: https://stackoverflow.com/questions/52805115/certificate-verify-failed-unable-to-get-local-issuer-certificate

このコードを に追加してみましょうrequest。まず、どのスキームが使用されているかを検出する必要があります。

``` {.python}
import ssl

class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]
        # ...
```

(ここでは、既存のスキーム解析コードをこの新しいコードに置き換える必要があることに注意してください。通常、コンテキストとコード自体から、何を置き換える必要があるかは明らかです。)

暗号化された HTTP 接続では通常、ポート 80 ではなくポート 443 が使用されます。

``` {.python expected=False}
class URL:
    def __init__(self, url):
        # ...
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443
```

ソケットを作成するときにそのポートを使用できます。

``` {.python}
class URL:
    def request(self):
        # ...
        s.connect((self.host, self.port))
        # ...
```

次に、ソケットをsslライブラリでラップします。

``` {.python}
class URL:
    def request(self):
        # ...
        s.connect((self.host, self.port))
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        # ...
```

これでブラウザは HTTPS サイトに接続できるようになります。

ついでに、図 6 のように、ホスト名の後にコロンを付けて URL で指定するカスタム ポートのサポートを追加しましょう。

::: {.cmd .web-only html=True}
    python3 infra/annotate_code.py <<EOF
    http://example.org:[8080][tl|Port]/index.html
    EOF
:::

::: {.center .web-only}
Figure 6: Where the port goes in a URL.
:::

::: {.print-only}
![図 6: URL 内でのポートの位置](im/http-ports.png)
:::

URL にポートがある場合は、それを解析して使用できます。

``` {.python}
class URL:
    def __init__(self, url):
        # ...
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
```

カスタムポートはデバッグに便利です。Pythonには、コンピュータ上でファイルを提供できる組み込みのWebサーバーがあります。たとえば、

``` {.sh}
python3 -m http.server 8000 -d /some/directory
```

すると、http://localhost:8000/そのディレクトリ内のすべてのファイルが表示されます。これはブラウザをテストするのに適した方法です。

::: {.further}
TLS は非常に複雑です。詳細はRFC 8446で確認できますが、独自に実装することはお勧めしません。正しいだけでなく安全なカスタム TLS 実装を書くのは非常に困難です。
:::

この時点で、任意の Web ページでプログラムを実行できるはずです。簡単な例の出力は次のようになります。

[example-simple]: examples/example1-simple.html

``` {.output}

  
    This is a simple
    web page with some
    text in it.
  

```

まとめ
=======

この章では、空のファイルから、次のことができる基本的な Web ブラウザーを作成しました。


-   URL をスキーム、ホスト、ポート、パスに解析します。
-   socketおよび ライブラリを使用してそのホストに接続しますssl
-   ヘッダーを含む HTTP リクエストをそのホストに送信しますHost 。
-   HTTP 応答をステータス行、ヘッダー、本文に分割します。
-   本文にテキスト（タグではない）を印刷します。

はい、これはまだ Web ブラウザというよりはコマンドライン ツールですが、ブラウザのコア機能の一部はすでに備えています。

::: {.signup}
:::

概要
=======

ブラウザ内の関数、クラス、メソッドの完全なセットは次のようになります。

::: {.web-only .cmd .python .outline html=True}
    python3 infra/outlines.py --html src/lab1.py --template book/outline.txt
:::

::: {.print-only .cmd .python .outline}
    python3 infra/outlines.py src/lab1.py --template book/outline.txt
:::


演習
=========

1-1 HTTP/1.1。 とともにHost、 関数Connectionで ヘッダーを のrequest値とともに送信しますclose。これで、ブラウザは を使用していることを宣言できますHTTP/1.1。また、User-Agentヘッダーを追加します。その値は任意の値にすることができます。この値は、ホストに対してブラウザを識別します。将来的にさらにヘッダーを追加しやすくなります。

1-2ファイル URL。 スキームのサポートを追加しますfile。これにより、ブラウザーでローカル ファイルを開くことができます。たとえば、 は file:///path/goes/hereコンピューター上の場所 にあるファイルを参照する必要があります/path/goes/here。また、URL を指定せずにブラウザーを起動すると、コンピューター上の特定のファイルが開かれるようにします。そのファイルを使用して、簡単なテストを行うことができます。

1-3 data。さらに別のスキームとして があり data、これを使用すると、HTML コンテンツを URL 自体にインライン化できます。data:text/html,Hello world!実際のブラウザで に移動して、何が起こるかを確認してください。ブラウザにこのスキームのサポートを追加してください。このdataスキームは、テストを別のファイルに配置せずに作成するのに特に便利です。

1-4エンティティ。小なり ( &lt;) エンティティと大なり ( ) エンティティのサポートを実装します。これらは、それぞれと &gt;として印刷されます。たとえば、HTML 応答が の場合 、ブラウザの メソッドは を印刷します。エンティティを使用すると、ブラウザがタグとして解釈することなく、Web ページにこれらの特殊文字を含めることができます。<>&lt;div&gt;show<div>

1-5 view-source。スキームのサポートを追加します view-source。 に移動すると、 view-source:http://example.org/レンダリングされたページではなく HTML ソースが表示されます。 このスキームのサポートを追加します。 ブラウザは、HTML ファイル全体をテキストのように印刷します。 演習 1-4 も実装しておく必要があります。

1-6キープアライブ。演習 1-1 を実装します。ただし、ヘッダーは送信しませんConnection: close( Connection: keep-alive代わりに を送信します)。ソケットから本体を読み取るときは、ヘッダーで指定されたバイト数だけを読み取り Content-Length、その後ソケットを閉じません。代わりに、ソケットを保存し、同じサーバーに別の要求が行われた場合は、新しいソケットを作成するのではなく、同じソケットを再利用します。("rb"にオプションを渡す必要もあります。そうしないmakefileと、 によって報告される値が、Content-Length読み取っている文字列の長さと一致しない可能性があります。) これにより、よくある同じサーバーへの繰り返しの要求が高速化されます。

1-7リダイレクト。300 の範囲のエラー コードではリダイレクトが要求されます。ブラウザーがリダイレクトに遭遇すると、Locationヘッダーに指定された URL に新しい要求が行われます。 Locationヘッダーは完全な URL である場合もありますが、ホストとスキームをスキップして で始まる場合も/あります (つまり、元の要求と同じホストとスキーム)。新しい URL 自体がリダイレクトである場合もあるので、その場合は必ず処理してください。ただし、リダイレクト ループにはまりたくないので、ブラウザーが連続して実行できるリダイレクトの数を制限するようにしてください。このページにリダイレクトする URL http://browser.engineering/redirectと、より複雑なリダイレクト チェーンを実行する/redirect2および/redirect3の類似 URL でこれをテストできます。

1-8キャッシュGET。通常、同じ画像、スタイル、スクリプトが複数のページで使用されているため、それらを繰り返しダウンロードするのは無駄です。HTTP 応答が要求され、応答を受け取った限り、HTTP 応答をキャッシュすることは一般的に有効です200。301やなどの他のステータス コード 404もキャッシュできます。 ブラウザにキャッシュを実装し、同じファイルを複数回要求してテストします。サーバーはヘッダーを使用してキャッシュを制御します 。このヘッダー、特にと の値Cache-Controlのサポートを追加します 。ヘッダーにこれら 2 つ以外の値が含まれている場合は、応答をキャッシュしないことをお勧めします。no-storemax-ageCache-Control

1-9圧縮。HTTP 圧縮のサポートを追加します。これにより、ブラウザはサーバーに圧縮されたデータが受け入れ可能であることを通知します。ブラウザは、Accept-Encoding値 のヘッダー を送信する必要がありますgzip。サーバーが圧縮をサポートしている場合、その応答にはContent-Encoding値 のヘッダー が含まれます。その後、本体は圧縮されます。このケースのサポートを追加します。データを解凍するには、モジュール の メソッドgzipを使用できます。GZip データは-encodedではない ため、代わりに生のバイトを処理するには に 渡します。ほとんどの Web サーバーは、と呼ばれるで圧縮データを送信します。decompressgziputf8"rb"makefileTransfer-EncodingchunkedTransfer-Encodingデータを圧縮する もいくつかありますが 、あまり使用されません。そのためのサポートも追加する必要があります


[negotiate]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Content_negotiation

[chunked]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Transfer-Encoding

[^te-gzip]: Transfer-Encodingデータを圧縮する もいくつかありますが 、あまり使用されません。
