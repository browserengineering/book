html := $(patsubst book/%.md,www/%.html,$(wildcard book/*.md))

all: $(html)

www/%.html: book/%.md book/template.html book/signup.html book/filter.lua
	pandoc --template book/template.html --include-after-body book/signup.html -c book.css --from markdown --to html --lua-filter=book/filter.lua \
	    $< -o $@

publish:
	rsync -r --exclude=*.pickle --exclude=*.hash www/ server:/home/www/browseng/
	ssh server chmod -Rf a+r /home/www/browseng/ || true
	ssh server sudo systemctl restart browser-engineering.service

download:
	rsync -r 'server:/home/www/browseng/*.pickle' www/

clean:
	rm $(html)
