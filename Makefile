html := $(patsubst book/%.md,www/%.html,$(wildcard book/*.md))
blog := $(patsubst blog/%.md,www/blog/%.html,$(wildcard blog/*.md))
FLAGS=

all: $(html) $(blog)
draft: $(patsubst www/%.html,www/draft/%.html,$(html))

www/%.html: book/%.md book/template.html book/signup.html book/filter.lua disabled.conf
	pandoc --toc --template book/template.html $(FLAGS) -c book.css --variable=script:feedback.js --from markdown --to html --lua-filter=book/filter.lua $< -o $@

www/blog/%.html: blog/%.md book/template.html book/filter.lua disabled.conf
	pandoc --metadata=toc:none --template book/template.html $(FLAGS) -c ../book.css --from markdown --to html --lua-filter=book/filter.lua $< -o $@

www/draft/%.html: book/%.md book/template.html book/signup.html book/filter.lua
	pandoc --toc --template book/template.html $(FLAGS) \
	       --metadata=mode:draft --variable=script:../feedback.js \
               --variable=script:../outline.js --variable=script:outlines_data.js \
               -c ../book.css --from markdown --to html --lua-filter=book/filter.lua \
               $< -o $@

www/draft/outlines_data.js: $(wildcard src/*.py)
	python3 atlas.py --output "$@" $^

publish: all
	rsync -r --exclude=*.pickle --exclude=*.hash www/ server:/home/www/browseng/
	ssh server chmod -Rf a+r /home/www/browseng/ || true
	ssh server sudo systemctl restart browser-engineering.service

download:
	rsync -r 'server:/home/www/browseng/*.pickle' www/

clean:
	rm $(html)
