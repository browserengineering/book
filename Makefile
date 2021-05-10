FLAGS=

ORDERED_PAGES=preface intro history http graphics text html layout styles chrome forms scripts reflow security visual-effects skipped change glossary

PANDOC_COMMON_ARGS=$(FLAGS) --from markdown --to html --lua-filter=book/filter.lua --fail-if-warnings --metadata-file=config.json

WIDGET_LAB_CODE=lab2.js lab3.js lab5.js

book: $(patsubst book/%.md,www/%.html,$(wildcard book/*.md)) www/rss.xml $(patsubst %,www/widgets/%,$(WIDGET_LAB_CODE))
blog: $(patsubst blog/%.md,www/blog/%.html,$(wildcard blog/*.md)) www/rss.xml
draft: $(patsubst book/%.md,www/draft/%.html,$(wildcard book/*.md)) www/draft/onepage.html $(patsubst %,www/widgets/%,$(WIDGET_LAB_CODE))

onepage/%.html: book/%.md book/template-onepage.html book/filter.lua disabled.conf
	mkdir -p $(dir $@)
	pandoc --toc --template book/template-onepage.html --variable=base=../ --variable=rel=onepage -c book.css $(PANDOC_COMMON_ARGS) --metadata=mode:draft -c ../book.css $< -o $@

onepage/%-quicklink.html: book/%.md book/quicklink.html book/filter.lua disabled.conf
	mkdir -p $(dir $@)
	pandoc --toc --template book/quicklink.html --variable=base=../ --variable=rel=onepage $(PANDOC_COMMON_ARGS) $< -o $@

www/draft/onepage.html: $(patsubst book/%.md,onepage/%.html,$(wildcard book/*.md)) $(patsubst book/%.md,onepage/%-quicklink.html,$(wildcard book/*.md)) book/onepage-head.html
	mkdir -p $(dir $@)
	cat book/onepage-head.html  $(patsubst %,onepage/%-quicklink.html,$(ORDERED_PAGES)) $(patsubst %,onepage/%.html,$(ORDERED_PAGES)) > www/draft/onepage.html

www/%.html: book/%.md book/template.html book/signup.html book/filter.lua disabled.conf
	mkdir -p $(dir $@)
	pandoc --toc --template book/template.html  --variable=rel=. \
			-c book.css $(PANDOC_COMMON_ARGS) $< -o $@

www/rss.xml: book/news.yaml book/rss-template.xml
	pandoc --template book/rss-template.xml  -f markdown -t html $< -o $@

www/blog/%.html: blog/%.md book/template.html book/filter.lua disabled.conf
	mkdir -p $(dir $@)
	pandoc --metadata=toc:none --variable=base=../  --variable=rel=blog --template book/template.html -c book.css $(PANDOC_COMMON_ARGS) $< -o $@

www/draft/%.html: book/%.md book/template.html book/signup.html book/filter.lua
	@ mkdir -p $(dir $@)
	pandoc --toc --template book/template.html \
	       --metadata=mode:draft --variable=base=../ --variable=rel=draft \
               -c book.css $(PANDOC_COMMON_ARGS) \
               $< -o $@

www/widgets/%.js: src/%.py
	python3 ./compile.py $< $@ --hints src/$*.hints

publish:
	rsync -rtu --exclude=*.pickle --exclude=*.hash www/ server:/home/www/browseng/
	ssh server chmod -Rf a+r /home/www/browseng/ || true
	ssh server sudo systemctl restart browser-engineering.service

download:
	rsync -r 'server:/home/www/browseng/*.pickle' www/

clean:
	rm $(html)
