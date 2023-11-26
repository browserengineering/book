-- Pass 1: Load configuration data

local config = nil
local chapters = nil
local mode = nil

local main = nil

function LoadMeta(meta)
  if not meta.mode then meta.mode = "book" end
  config = meta.modes[meta.mode]
  chapters = meta.chapters
  mode = meta.mode
  if not config then error("Invalid mode " .. meta.mode) end

  meta.rel = config.rel
  meta.base = config.base
  meta.draft = config.draft

  if meta.main then
    main = true
  end
  return meta
end

-- Pass 2: Implement disabled links, footnotes, and custom blocks

function is_disabled(link)
   return not config.show_disabled and chapters[link] and chapters[link].disabled
end

function DisableMeta(meta)
  if meta.prev and is_disabled(tostring(meta.prev[1].text) .. ".md") then
    meta.prev = nil
  end
  if meta.next and is_disabled(tostring(meta.next[1].text) .. ".md") then
    meta.next = nil
  end
  return meta
end

function DisableLinks(el)
  -- Links to Markdown files now link to HTML files
  if is_disabled(el.target) then
    el = pandoc.Span(el.content)
    el.classes = { "link" }
  elseif el.target:find("%.md$") and not el.target:find("://") then
    el.target = string.gsub(el.target, "%.md", ".html")
  elseif el.target:find("%.md#") and not el.target:find("://") then
    el.target = string.gsub(el.target, "%.md#", ".html#")
  end
  return el
end

function Note(el)
  if mode == "book" then
    -- Footnotes become margin notes
    note = pandoc.Span(el.content[1].content)
    note.classes = { "note" }
    wrapper = pandoc.Span { note }
    wrapper.classes = { "note-container" }
    return wrapper
  else
    return el
  end
end

function Div(el)
  if not config.show_todos and el.classes[1] == "todo" then
    return pandoc.RawBlock("html", "")
  elseif not config.print and el.classes[1] == "print-only" then
    return pandoc.RawBlock("html", "")
  elseif config.print and el.classes[1] == "web-only" then
    return pandoc.RawBlock("html", "")
  elseif config.show_signup and el.classes[1] == "signup" then
    local signup = assert(io.open("infra/signup.html")):read("*all")
    return pandoc.RawBlock("html", signup)
  elseif el.classes[1] == "widget" then
    if #el.content ~= 1 or
       el.content[1].t ~= "CodeBlock" then
      error("`widget` block does not contain a code block")
    end
    local url = (config.base and config.base[1].text or "") .. "widgets/" .. el.content[1].text
    local src = "<iframe class=\"widget\" src=\"" .. url .. "\""
    if el.attributes["height"] then
       src = src .. " height=\"" .. el.attributes["height"] .. "\""
    end
    if el.attributes["big-height"] then
       src = src .. " data-big-height=\"" .. el.attributes["big-height"] .. "\""
    end
    if el.attributes["small-height"] then
       src = src .. " data-small-height=\"" .. el.attributes["small-height"] .. "\""
    end
    src = src .. "></iframe>"
    return pandoc.RawBlock("html", src)
  elseif el.classes[1] == "cmd" or el.classes[2] == "cmd" then
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

-- Pass 3: Collect and insert a table of contents

local headers = pandoc.List()

function Header(el)
   headers:insert(el)
end

function Doc(el)
   if main or not config.show_toc then
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

-- Set up and return the three passes

return { 
  { Meta = LoadMeta },
  { Meta = DisableMeta, Link = DisableLinks, Note = Note, Div = Div },
  { Header = Header, Doc = Doc },
}
