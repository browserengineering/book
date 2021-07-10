.PHONY: book blog draft widgets publish clean download wc lint

FLAGS=

CHAPTERS=$(patsubst book/%.md,%,$(wildcard book/*.md))
WIDGET_LAB_CODE=lab2 lab3 lab5 lab7

book: $(patsubst %,www/%.html,$(CHAPTERS)) www/rss.xml widgets
blog: $(patsubst blog/%.md,www/blog/%.html,$(wildcard blog/*.md)) www/rss.xml
draft: $(patsubst %,www/draft/%.html,$(CHAPTERS)) www/onepage.html widgets
widgets: $(patsubst lab%,www/widgets/lab%-browser.html,$(WIDGET_LAB_CODE)) www/widgets/rt-module.js

lint: book/*.md src/*.py
	python3 infra/compare.py --config config.json

PANDOC=pandoc --from markdown --to html --lua-filter=infra/filter.lua --fail-if-warnings --metadata-file=config.json $(FLAGS)

www/%.html: book/%.md infra/template.html infra/signup.html infra/filter.lua config.json
	$(PANDOC) --toc --metadata=mode:book --template infra/template.html -c book.css $< -o $@

www/blog/%.html: blog/%.md infra/template.html infra/filter.lua config.json
	$(PANDOC) --metadata=mode:blog --template infra/template.html -c book.css $< -o $@

www/draft/%.html: book/%.md infra/template.html infra/signup.html infra/filter.lua config.json
	$(PANDOC) --toc --metadata=mode:draft --template infra/template.html -c book.css $< -o $@

www/rss.xml: news.yaml infra/rss-template.xml
	pandoc --template infra/rss-template.xml  -f markdown -t html $< -o $@

www/widgets/lab2.js: src/lab2.py src/lab2.hints infra/compile.py
	python3 infra/compile.py $< $@ --hints src/lab2.hints --use-js-modules

www/widgets/lab3.js: src/lab3.py src/lab2.hints infra/compile.py
	python3 infra/compile.py $< $@ --hints src/lab3.hints --use-js-modules

www/widgets/lab%.js: src/lab%.py src/lab%.hints infra/compile.py
	python3 infra/compile.py $< $@ --hints src/lab$*.hints

www/widgets/rt-module.js: www/widgets/rt.js
	echo "export { breakpoint, http_textarea, lib, pysplit, rt_constants, truthy, Widget };" > www/widgets/rt-module.js
	cat www/widgets/rt.js >> www/widgets/rt-module.js

www/widgets/lab%-browser.html: infra/labN-browser.html infra/labN-browser.lua config.json www/widgets/lab%.js
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

test:
	(cd src/ && python3 -m doctest lab1-tests.md)
	python3 -m doctest infra/compiler.md
