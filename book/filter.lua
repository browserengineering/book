require "os"

-- Links in disabled.conf disabled unless mode is set to draft
local disabled = {}
local draft = nil
local main = nil
local toc = true

function Meta (meta)
  if meta.mode == "draft" then
    draft = true
  else
    disabled = meta.disabled_files
  end
  if meta.main then
    main = true
  end
  if meta.toc == "none" then
     toc = nil
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
  elseif (not draft and el.classes[1] == "signup")
  or (main and not draft and el.classes[1] == "warning") then
    local signup = assert(io.open("book/signup.html")):read("*all")
    return pandoc.RawBlock("html", signup)
  elseif el.classes[1] == "cmd" then
    if #el.content ~= 1 or
       el.content[1].t ~= "CodeBlock" then
      error("`cmd` block does not contain a code block")
    end
    local cmd = el.content[1].text
    local proc = io.popen(cmd)
    local results = proc:read("*all")
    local pre = nil
    if el.attributes["html"] then
       pre = pandoc.Div({ pandoc.RawBlock("html", results) })
    else
       pre = pandoc.CodeBlock(results)
    end
    pre.classes = el.classes
    return pre
  else
    return el
  end
end

local headers = pandoc.List()

function Header(el)
   headers:insert(el)
end

function Doc(el)
   if main or not toc then
      return el
   end
   -- Find where to put the in-line TOC
   local idx = 1
   for i, v in ipairs(el.blocks) do
      if v.tag == "Header" then
         idx = i
         break
      end
   end
   -- Insert it
   local items = pandoc.List()
   for i, v in ipairs(headers) do
      local content = pandoc.Para({ pandoc.Link(v.content, "#" .. v.identifier) })
      table.insert(items, content)
   end
   local toc = pandoc.Div({ pandoc.BulletList(items) })
   toc.identifier = "toc"
   table.insert(el.blocks, idx, toc)
   return el
end

return { 
  { Meta = Meta },
  { Link = Link, Note = Note, Div = Div },
  { Header = Header, Doc = Doc },
}
