.PHONY: book blog draft widgets publish clean download

FLAGS=

CHAPTERS=$(patsubst book/%.md,%,$(wildcard book/*.md))
WIDGET_LAB_CODE=lab2.js lab3.js lab5.js

book: $(patsubst %,www/%.html,$(CHAPTERS)) www/rss.xml widgets
blog: $(patsubst blog/%.md,www/blog/%.html,$(wildcard blog/*.md)) www/rss.xml
draft: $(patsubst %,www/draft/%.html,$(CHAPTERS)) www/onepage.html widgets
widgets: $(patsubst %,www/widgets/%,$(WIDGET_LAB_CODE))

PANDOC=pandoc --from markdown --to html --lua-filter=book/filter.lua --fail-if-warnings --metadata-file=config.json $(FLAGS)

www/%.html: book/%.md book/template.html book/signup.html book/filter.lua config.json
	$(PANDOC) --toc --metadata=mode:book --template book/template.html -c book.css $< -o $@

www/blog/%.html: blog/%.md book/template.html book/filter.lua config.json
	$(PANDOC) --metadata=mode:blog --template book/template.html -c book.css $< -o $@

www/draft/%.html: book/%.md book/template.html book/signup.html book/filter.lua config.json
	$(PANDOC) --toc --metadata=mode:draft --template book/template.html -c book.css $< -o $@

www/rss.xml: book/news.yaml book/rss-template.xml
	pandoc --template book/rss-template.xml  -f markdown -t html $< -o $@

www/widgets/%.js: src/%.py
	python3 ./compile.py $< $@ --hints src/$*.hints

www/onepage/%.html: book/%.md book/chapter.html book/filter.lua config.json
	$(PANDOC) --toc --metadata=mode:onepage --variable=cur:$* --template book/chapter.html $< -o $@

www/onepage.html: $(patsubst %,www/onepage/%.html,$(CHAPTERS))
www/onepage.html: book/onepage.md book/template.html book/filter.lua config.json
	$(PANDOC) --metadata=mode:onepage --template book/template.html -c book.css $< -o $@

publish:
	rsync -rtu --exclude=*.pickle --exclude=*.hash www/ server:/home/www/browseng/
	ssh server chmod -Rf a+r /home/www/browseng/ || true
	ssh server sudo systemctl restart browser-engineering.service

download:
	rsync -r 'server:/home/www/browseng/*.pickle' www/

clean:
	rm $(html)
