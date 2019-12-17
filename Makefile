html := $(patsubst book/%.md,www/%.html,$(wildcard book/*.md))

all: $(html)

www/%.html: book/%.md book/template.html book/filter.lua
	pandoc --template book/template.html -c book.css --from markdown --to html --lua-filter=book/filter.lua \
	    $< -o $@

publish:
	rsync -r --exclude=*.pickle --exclude=*.hash www/ server:/home/www/browseng/
	ssh server chmod -Rf a+r /home/www/browseng/ || true

download:
	rsync -r 'server:/home/www/browseng/*.pickle' 'server:/home/www/browseng/*.hash' www/

clean:
	rm $(html)
