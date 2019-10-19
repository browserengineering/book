-- Links to Markdown files now link to HTML files
function Link(el)
  el.target = string.gsub(el.target, "%.md", ".html")
  return el
end

-- Footnotes become margin notes
function Note(el)
  note = pandoc.Span(el.content[1].content)
  note.classes = { "note" }
  wrapper = pandoc.Span { note }
  wrapper.classes = { "note-container" }
  return wrapper
end
