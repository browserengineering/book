.PHONY: book blog draft widgets publish clean download wc lint examples

FLAGS=

CHAPTERS=$(patsubst book/%.md,%,$(wildcard book/*.md))
WIDGET_LAB_CODE=lab1 lab2 lab3 lab4 lab5 lab6 lab7

EXAMPLE_HTML=$(patsubst src/example%.html,%,$(wildcard src/example*.html))
EXAMPLE_JS=$(patsubst src/example%.js,%,$(wildcard src/example*.js))
EXAMPLE_CSS=$(patsubst src/example%.css,%,$(wildcard src/example*.css))

book: $(patsubst %,www/%.html,$(CHAPTERS)) www/rss.xml widgets examples
blog: $(patsubst blog/%.md,www/blog/%.html,$(wildcard blog/*.md)) www/rss.xml
draft: $(patsubst %,www/draft/%.html,$(CHAPTERS)) www/onepage.html widgets
widgets: $(patsubst lab%,www/widgets/lab%-browser.html,$(WIDGET_LAB_CODE)) $(patsubst lab%,www/widgets/lab%.js,$(WIDGET_LAB_CODE))
examples: $(patsubst %,www/examples/example%.html,$(EXAMPLE_HTML)) \
	$(patsubst %,www/examples/example%.js,$(EXAMPLE_JS)) \
	$(patsubst %,www/examples/example%.css,$(EXAMPLE_CSS))

lint: book/*.md src/*.py
	python3 infra/compare.py --config config.json
	! grep -n '^```' book/*.md | awk '(NR % 2) {print}' | grep -v '{.'

PANDOC=pandoc --from markdown --to html --lua-filter=infra/filter.lua --fail-if-warnings --metadata-file=config.json $(FLAGS)

www/%.html: book/%.md infra/template.html infra/signup.html infra/filter.lua config.json
	$(PANDOC) --toc --metadata=mode:book --template infra/template.html -c book.css $< -o $@

www/blog/%.html: blog/%.md infra/template.html infra/filter.lua config.json
	$(PANDOC) --metadata=mode:blog --template infra/template.html -c book.css $< -o $@

www/draft/%.html: book/%.md infra/template.html infra/signup.html infra/filter.lua config.json
	$(PANDOC) --toc --metadata=mode:draft --template infra/template.html -c book.css $< -o $@

www/rss.xml: news.yaml infra/rss-template.xml
	pandoc --template infra/rss-template.xml  -f markdown -t html $< -o $@

www/widgets/lab%.js: src/lab%.py src/lab%.hints infra/compile.py
	python3 infra/compile.py $< $@ --hints src/lab$*.hints --use-js-modules

www/widgets/lab%-browser.html: infra/labN-browser.html infra/labN-browser.lua config.json www/widgets/lab%.js
	pandoc --lua-filter=infra/labN-browser.lua --metadata-file=config.json --metadata chapter=$* --template $< book/index.md -o $@

www/examples/%.html: src/%.html
	cp $< www/examples

www/examples/%.js: src/%.js
	cp $< www/examples

www/examples/%.css: src/%.css
	cp $< www/examples

www/onepage/%.html: book/%.md infra/chapter.html infra/filter.lua config.json
	$(PANDOC) --toc --metadata=mode:onepage --variable=cur:$* --template infra/chapter.html $< -o $@

www/onepage.html: $(patsubst %,www/onepage/%.html,$(CHAPTERS))
www/onepage.html: book/onepage.md infra/template.html infra/filter.lua config.json
	$(PANDOC) --metadata=mode:onepage --template infra/template.html -c book.css $< -o $@

wc:
	@ printf " Words  Code  File\n"; awk -f infra/wc.awk book/*.md | sort -rn

publish:
	rsync -rtu --exclude=*.pickle --exclude=*.hash www/ server:/home/www/browseng/
	ssh server chmod -Rf a+r /home/www/browseng/ || true

restart:
	rsync infra/api.py server:/home/www/browseng/
	ssh server sudo systemctl restart browser-engineering.service

download:
	rsync -r 'server:/home/www/browseng/*.pickle' www/

backup:
	rsync server:/home/www/browseng/db.pickle infra/db.$(shell date +%Y-%m-%d).pickle

test:
	set -e; \
	for i in $$(seq 1 14); do \
		(cd src/ && PYTHONBREAKPOINT=0 python3 -m doctest lab$$i-tests.md); \
	done
	python3 -m doctest infra/compiler.md
	python3 -m doctest infra/annotate_code.md
