FLAGS=

book: $(patsubst book/%.md,www/%.html,$(wildcard book/*.md))
blog: $(patsubst blog/%.md,www/blog/%.html,$(wildcard blog/*.md))
draft: $(patsubst book/%.md,www/draft/%.html,$(wildcard book/*.md))

www/%.html: book/%.md book/template.html book/signup.html book/filter.lua disabled.conf
	mkdir -p $(dir $@)
	pandoc --toc --template book/template.html $(FLAGS) -c book.css --variable=script:feedback.js --from markdown --to html --lua-filter=book/filter.lua $< -o $@

www/blog/%.html: blog/%.md book/template.html book/filter.lua disabled.conf
	mkdir -p $(dir $@)
	pandoc --metadata=toc:none --template book/template.html $(FLAGS) -c ../book.css --from markdown --to html --lua-filter=book/filter.lua $< -o $@

www/draft/%.html: book/%.md book/template.html book/signup.html book/filter.lua
	@ mkdir -p $(dir $@)
	pandoc --toc --template book/template.html $(FLAGS) \
	       --metadata=mode:draft --variable=script:../feedback.js \
               -c ../book.css --from markdown --to html --lua-filter=book/filter.lua \
               $< -o $@

publish:
	rsync -rtu --exclude=*.pickle --exclude=*.hash www/ server:/home/www/browseng/
	ssh server chmod -Rf a+r /home/www/browseng/ || true
	ssh server sudo systemctl restart browser-engineering.service

download:
	rsync -r 'server:/home/www/browseng/*.pickle' www/

clean:
	rm $(html)
