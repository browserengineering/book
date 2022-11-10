.PHONY: book draft widgets publish clean download wc lint examples

FLAGS=

CHAPTERS=$(patsubst book/%.md,%,$(wildcard book/*.md))
WIDGET_LAB_CODE=lab1 lab2 lab3 lab4 lab5 lab6 lab7

EXAMPLE_HTML=$(patsubst src/example%.html,%,$(wildcard src/example*.html))
EXAMPLE_JS=$(patsubst src/example%.js,%,$(wildcard src/example*.js))
EXAMPLE_CSS=$(patsubst src/example%.css,%,$(wildcard src/example*.css))

book: $(patsubst %,www/%.html,$(CHAPTERS)) www/rss.xml widgets examples
draft: $(patsubst %,www/draft/%.html,$(CHAPTERS)) www/onepage.html widgets
examples: $(patsubst %,www/examples/example%.html,$(EXAMPLE_HTML)) \
	$(patsubst %,www/examples/example%.js,$(EXAMPLE_JS)) \
	$(patsubst %,www/examples/example%.css,$(EXAMPLE_CSS))

widgets: \
	www/widgets/lab2-browser.html www/widgets/lab2.js \
	www/widgets/lab3-browser.html www/widgets/lab3.js \
	www/widgets/lab4-browser.html www/widgets/lab4.js \
	www/widgets/lab5-browser.html www/widgets/lab5.js \
	www/widgets/lab6-browser.html www/widgets/lab6.js \
	www/widgets/lab7-browser.html www/widgets/lab7.js \
	www/widgets/lab8-browser.html www/widgets/lab8.js www/widgets/server8.js \
	www/widgets/lab9-browser.html www/widgets/lab9.js www/widgets/server9.js \
	www/widgets/lab10-browser.html www/widgets/lab10.js www/widgets/server10.js

src/lab%.full.py: src/lab%.py
	python3 infra/inline.py $< > $@

lint: book/*.md src/*.py
	python3 infra/compare.py --config config.json
	! grep -n '^```' book/*.md | awk '(NR % 2) {print}' | grep -v '{.'

PANDOC=pandoc --from markdown --to html --lua-filter=infra/filter.lua --fail-if-warnings --metadata-file=config.json $(FLAGS)

www/%.html: book/%.md infra/template.html infra/signup.html infra/filter.lua config.json
	$(PANDOC) --toc --metadata=mode:book --template infra/template.html -c book.css $< -o $@

www/draft/%.html: book/%.md infra/template.html infra/signup.html infra/filter.lua config.json
	$(PANDOC) --toc --metadata=mode:draft --template infra/template.html -c book.css $< -o $@

www/rss.xml: news.yaml infra/rss-template.xml
	pandoc --template infra/rss-template.xml  -f markdown -t html $< -o $@

www/widgets/lab%.js: src/lab%.py src/lab%.hints infra/compile.py
	python3 infra/compile.py $< $@ --hints src/lab$*.hints

www/widgets/server%.js: src/server%.py src/server%.hints infra/compile.py
	python3 infra/compile.py $< $@ --hints src/server$*.hints

www/onepage/%.html: book/%.md infra/chapter.html infra/filter.lua config.json
	$(PANDOC) --toc --metadata=mode:onepage --variable=cur:$* --template infra/chapter.html $< -o $@

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
	rsync server:/home/www/browseng/db.json infra/db.$(shell date +%Y-%m-%d).pickle

test-server:
	(cd www/ && python3 ../infra/server.py)

test:
	python3 -m doctest infra/compiler.md
	python3 -m doctest infra/annotate_code.md
	set -e; \
	for i in $$(seq 1 14); do \
		(cd src/ && python3 -m doctest lab$$i-tests.md); \
	done

test-allinone:
	(cd src/ && python3 -m doctest lab13_allinone-tests.md);
