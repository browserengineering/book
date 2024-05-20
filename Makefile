.PHONY: book draft widgets publish clean download wc lint examples

FLAGS=

CHAPTERS=\
preface intro history \
http graphics text \
html layout styles chrome \
forms scripts security \
visual-effects scheduling animations accessibility embeds invalidation \
skipped change \
glossary bibliography about classes porting

EXAMPLE_HTML=$(patsubst src/example%.html,%,$(wildcard src/example*.html))
EXAMPLE_JS=$(patsubst src/example%.js,%,$(wildcard src/example*.js))
EXAMPLE_CSS=$(patsubst src/example%.css,%,$(wildcard src/example*.css))

book: $(patsubst %,www/%.html,$(CHAPTERS)) www/rss.xml widgets examples www/index.html
draft: $(patsubst %,www/draft/%.html,$(CHAPTERS)) www/onepage.html widgets
examples: $(patsubst %,www/examples/example%.html,$(EXAMPLE_HTML)) \
	$(patsubst %,www/examples/example%.js,$(EXAMPLE_JS)) \
	$(patsubst %,www/examples/example%.css,$(EXAMPLE_CSS))

widgets: \
	www/widgets/lab1.js \
	www/widgets/lab2-browser.html www/widgets/lab2.js \
	www/widgets/lab3-browser.html www/widgets/lab3.js \
	www/widgets/lab4-browser.html www/widgets/lab4.js \
	www/widgets/lab5-browser.html www/widgets/lab5.js \
	www/widgets/lab6-browser.html www/widgets/lab6.js \
	www/widgets/lab7-browser.html www/widgets/lab7.js \
	www/widgets/lab8-browser.html www/widgets/lab8.js www/widgets/server8.js \
	www/widgets/lab9-browser.html www/widgets/lab9.js www/widgets/server9.js \
	www/widgets/lab10-browser.html www/widgets/lab10.js www/widgets/server10.js \
	www/widgets/lab11-browser.html www/widgets/lab11.js \
	www/widgets/lab12-browser.html www/widgets/lab12.js \
	www/widgets/lab13-browser.html www/widgets/lab13.js \
	www/widgets/lab14-browser.html www/widgets/lab14.js \
	www/widgets/lab15-browser.html www/widgets/lab15.js \
	www/widgets/lab16-browser.html www/widgets/lab16.js

src/lab%.full.py: src/lab%.py infra/inline.py infra/asttools.py
	python3 infra/inline.py $< > $@

CHAPTER=all

PANDOC=pandoc --number-sections --from markdown --to html --lua-filter=infra/filter.lua --fail-if-warnings --metadata-file=config.json --highlight-style=infra/wbecode.theme $(FLAGS)

PANDOC_LATEX=pandoc --number-sections --standalone --from markdown --to latex --fail-if-warnings --metadata-file=config.json --lua-filter=infra/filter.lua --highlight-style=infra/wbecode.theme $(FLAGS)

# Generates a simple chapter latex rendering meant to be inserted into the larger book skeleton.
latex-chapters: $(patsubst %,latex/%-chapter.tex,$(CHAPTERS))
latex/%-chapter.tex:  book/%.md infra/template-chapter.tex infra/filter.lua config.json
	$(PANDOC_LATEX) --metadata=mode:print --template infra/template-chapter.tex  $< -o $@

# Generates a skeleton latex output that has all of the setup necessary to render chapters.
latex/book-skeleton.tex: $(patsubst %,book/%.md,$(CHAPTERS)) infra/template-book.tex infra config.json
	$(PANDOC_LATEX) --file-scope --template infra/template-book.tex $(patsubst %,book/%.md,$(CHAPTERS)) --metadata=mode:print -o latex/book-skeleton.tex

# Inserts the chapters into the book skeleton.
latex/book.tex: latex/book-skeleton.tex latex-chapters
	cat $(patsubst %,latex/%-chapter.tex,$(CHAPTERS)) > latex/book-contents.tex
	sed '/---Contents---/r latex/book-contents.tex' latex/book-skeleton.tex > latex/book.tex
	rm latex/book-contents.tex
	sed -i.bak '/---Contents---/d' latex/book.tex

latex/book.pdf: latex/book.tex latex/macros.tex
	(cd latex && ln -f -s ../www/examples/ examples)
	(cd latex && ln -f -s ../www/im/ im)
	(cd latex && pdflatex book.tex)

www/%.html: book/%.md infra/template.html infra/signup.html infra/filter.lua config.json src/lab*.py
	$(PANDOC) --toc --metadata=mode:book --template infra/template.html -c book.css $< -o $@

www/draft/%.html: book/%.md infra/template.html infra/signup.html infra/filter.lua config.json
	$(PANDOC) --toc --metadata=mode:draft --template infra/template.html -c book.css $< -o $@

www/rss.xml: news.yaml infra/rss-template.xml
	pandoc --template infra/rss-template.xml  -f markdown -t html $< -o $@

www/widgets/lab%.js: src/lab%.py src/lab%.hints infra/compile.py infra/asttools.py src/runtime*.js
	python3 infra/compile.py $< $@ --hints src/lab$*.hints

www/widgets/server%.js: src/server%.py src/server%.hints infra/compile.py infra/asttools.py
	python3 infra/compile.py $< $@ --hints src/server$*.hints

www/onepage/%.html: book/%.md infra/chapter.html infra/filter.lua config.json src/lab*.py
	$(PANDOC) --toc --metadata=mode:onepage --variable=cur:$* --template infra/chapter.html $< -o $@
www/onepage/onepage.html: ;
www/onepage.html: $(patsubst %,www/onepage/%.html,$(CHAPTERS))
www/onepage.html: book/onepage.md infra/template.html infra/filter.lua config.json
	$(PANDOC) --metadata=mode:onepage --template infra/template.html -c book.css $< -o $@

bottle.py:
	curl -O https://raw.githubusercontent.com/bottlepy/bottle/0.12.23/bottle.py

wc:
	@ printf " Words  Code  File\n"; awk -f infra/wc.awk book/*.md | sort -rn

publish:
	rsync -rtu --exclude=db.json --exclude=*.hash www/ server:/var/www/wbe/
	ssh server chmod -Rf a+r /var/www/wbe/ || true

restart:
	rsync infra/api.py server:/var/www/wbe/
	ssh server sudo systemctl restart browser-engineering.service

backup:
	rsync server:/var/www/wbe/db.json infra/db.$(shell date +%Y-%m-%d).pickle

test-server:
	(cd www/ && python3 ../infra/server.py)

lint test:
	python3 -m doctest infra/compiler.md
	python3 -m doctest infra/annotate_code.md
	python3 infra/runtests.py config.json --chapter $(CHAPTER)
	! grep -n '^```' book/*.md | awk '(NR % 2) {print}' | grep -v '{.'
