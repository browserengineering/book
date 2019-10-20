html := $(patsubst book/%.md,www/%.html,$(wildcard book/*.md))

all: $(html)

www/%.html: book/%.md book/template.html book/filter.lua
	pandoc --template book/template.html -c book.css --from markdown --to html --lua-filter=book/filter.lua \
	    $< -o $@

publish:
	rsync -r www/ server:/home/www/browseng/
	ssh server chmod a+r -R /home/www/browseng/

clean:
	rm $(html)
