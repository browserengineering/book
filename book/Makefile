html := $(patsubst %.md,%.html,$(wildcard *.md))

all: $(html)

%.html: %.md template.html filter.lua
	pandoc --template template.html -c book.css --from markdown --to html --lua-filter=filter.lua \
	    $< -o $@

clean:
	rm $(html)
