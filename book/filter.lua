-- Links in disabled.conf disabled unless mode is set to draft
local disabled = {}
local draft = nil
local main = nil

function Meta (meta)
  if meta.mode == "draft" then
    draft = true
  else
    for line in io.lines("disabled.conf") do
      if string.len(line) > 1 and string.sub(line, 1, 2) ~= "#" then
        disabled[line] = true
      end
    end
  end
  if meta.main then
    main = true
  end
  -- and  
  if meta.prev then
    if disabled[tostring(meta.prev[1].text) .. ".md"] then
      -- io.write("Disabling previous pointer\n")
      meta.prev = nil
    end
  end
  if meta.next then
    if disabled[tostring(meta.next[1].text) .. ".md"] then
      -- io.write("Disabling next pointer\n")
      meta.next = nil
    end
  end
  return meta
end


-- Links to Markdown files now link to HTML files
function Link(el)
  if not draft and disabled[el.target] then
    -- io.write("Disabling link " .. el.target .. "\n")
    el2 = pandoc.Span(el.content)
    el2.classes = { "link" }
    return el2
  else
    el.target = string.gsub(el.target, "%.md", ".html")
    return el
  end
end

-- Footnotes become margin notes
function Note(el)
  note = pandoc.Span(el.content[1].content)
  note.classes = { "note" }
  wrapper = pandoc.Span { note }
  wrapper.classes = { "note-container" }
  return wrapper
end

function Div(el)
  if not draft and el.classes[1] == "todo" then
    -- io.write("Disabling todo block\n")
    return pandoc.Div
  elseif el.classes[1] == "signup" or (main and not draft and el.classes[1] == "warning") then
    local signup = assert(io.open("book/signup.html")):read("*all")
    return pandoc.RawBlock("html", signup)
  else
    return el
  end
end

return { 
  { Meta = Meta },
  { Link = Link, Note = Note, Div = Div },
}
