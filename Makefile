.PHONY: book blog draft widgets publish clean download wc lint

FLAGS=

CHAPTERS=$(patsubst book/%.md,%,$(wildcard book/*.md))
WIDGET_LAB_CODE=lab2.js lab3.js lab5.js

book: $(patsubst %,www/%.html,$(CHAPTERS)) www/rss.xml widgets
blog: $(patsubst blog/%.md,www/blog/%.html,$(wildcard blog/*.md)) www/rss.xml
draft: $(patsubst %,www/draft/%.html,$(CHAPTERS)) www/onepage.html widgets
widgets: $(patsubst %,www/widgets/%,$(WIDGET_LAB_CODE))

lint: book/*.md src/*.py
	python3 infra/compare.py --config config.json
	python3 -m doctest infra/compiler.md

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
	python3 infra/compile.py $< $@ --hints src/lab$*.hints

www/widgets/lab%-browser.html: infra/labN-browser.html infra/labN-browser.lua config.json
	pandoc --lua-filter=infra/labN-browser.lua --metadata-file=config.json --metadata chapter=$* --template $< book/index.md -o $@

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
