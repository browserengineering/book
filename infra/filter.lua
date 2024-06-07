-- Pass 1: Load configuration data

local json = require('infra/dkjson')

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
  meta.show_quiz = config.show_quiz
  meta.colorlinks = true

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
  elseif not config.print and el.target:find("%.md$") and not el.target:find("://") then
    el.target = string.gsub(el.target, "%.md", ".html")
  elseif not config.print and el.target:find("%.md#") and not el.target:find("://") then
    el.target = string.gsub(el.target, "%.md#", ".html#")
  elseif config.print and (el.target:find("%.md$") or el.target:find("%.md#"))
         and not el.target:find("://") then
    el = pandoc.Span(el.content)
    el.classes = { "link" } -- this does nothing, just there for parallelism with is_disabled
  end
  return el
end

function Note(el)
  if not config.print then
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
  if el.classes:includes("print-only", 0) then
     if config.print then
        local _, idx = el.classes:find("print-only", 0)
        el.classes:remove(idx)
     else
        return {}
     end
  elseif el.classes:includes("web-only", 0) then
     if not config.print then
        local _, idx = el.classes:find("web-only", 0)
        el.classes:remove(idx)
     else
        return {}
     end
  end

<<<<<<< HEAD
  -- Exclude quiz assets and other things
  if el.classes:includes("quiz") and not config.show_quiz then
     return {}
  end

  -- Multiple-choice quiz processing
  if el.classes[1] == 'mc-quiz' and config.show_quiz then
     return process_quiz(el)
||||||| parent of 8643201 (Quizzes are more visually distinct from the text)
  if el.classes[1] == 'mc-question' then
     return process_mc_quiz(el)
=======
  if el.classes[1] == 'mc-question' and not config.print then
     return process_mc_quiz(el)
>>>>>>> 8643201 (Quizzes are more visually distinct from the text)
  end

  if not config.show_todos and el.classes[1] == "todo" then
    return pandoc.RawBlock("html", "")
  elseif el.classes:includes("signup") then
    if config.show_signup then
       local signup = assert(io.open("infra/signup.html")):read("*all")
       return pandoc.RawBlock("html", signup)
    end
  elseif el.classes:includes("widget") then
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
  elseif el.classes:includes("cmd") then
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
  elseif el.classes:includes("transclude") then
    io.input(pandoc.utils.stringify(el.content))
    local div = pandoc.CodeBlock( io.read('a'))
    div.classes = el.classes
    return div
  elseif el.classes:includes("center") then
     if config.print then
        return latex_wrap(el, "center", nil)
     else
        return el
     end
  elseif #el.classes >= 1 then
     if config.print then
        return latex_wrap(el, "bookblock", table.concat(el.classes, ","))
     else
        return el
     end
  else
     return el
  end
end

function latex_wrap(el, env, args)
   -- Suggestion from https://tex.stackexchange.com/questions/525924/with-pandoc-how-to-apply-a-style-to-a-fenced-div-block
   local latex_args = args and ("{" .. args .. "}") or ""
   return {
         pandoc.RawBlock("latex", "\\begin{" .. env .. "}" .. latex_args),
         el,
         pandoc.RawBlock("latex", "\\end{" .. env .. "}"),
   }
end

-- Quiz handling routine
function process_quiz(el)
   local questions = split_list(el.content, pandoc.HorizontalRule())
   local parsed_questions = {}
   for i, e in ipairs(questions) do
      table.insert(parsed_questions, process_mc_question(pandoc.Div(e)))
   end

   local encoded = pandoc.json.encode({ questions = parsed_questions })

   return pandoc.Div(pandoc.Para(pandoc.Str('')),
                     pandoc.Attr('', {"quiz-placeholder"},
                                 {{"data-quiz-questions", encoded},
                                  {"data-quiz-name", pandoc.utils.stringify(el.identifier)}}))
end

function process_mc_question(el)
   -- expecting Div [ Para ..., BulletList [[Plain ...], ...], Para ...]
   -- check that everything looks good
   if el.content[1].tag ~= 'Para' then
      print('Expected paragraph at beginning of mc quiz block.')
      return
   end
   if el.content[2].tag ~= 'BulletList' then
      print('Expected bulleted list at middle of mc quiz block.')
      return
   end

   local prompt = pandoc.utils.stringify(el.content[1])
   local answer = pandoc.utils.stringify(el.content[2].content[1])
   local distractors = {}
   for i, v in ipairs({table.unpack(el.content[2].content, 2)}) do
      distractors[i] = pandoc.utils.stringify(v)
   end

   local context = ''
   if el.content[3] and el.content[3].tag == 'Para' then
      context = pandoc.utils.stringify(el.content[3].content)
   end

   local q = { type = "MultipleChoice",
               prompt = { prompt = prompt,
                          distractors = distractors },
               answer = { answer = answer },
               context = context }

   return q
end

-- Generic function to split list
function split_list(list, split_on)
    local result = {}
    local sublist = {}
    for i, el in ipairs(list) do
        if el == split_on then
            if #sublist > 0 then
                table.insert(result, sublist)
                sublist = {}
            end
        else
            table.insert(sublist, el)
        end
    end
    if #sublist > 0 then
        table.insert(result, sublist)
    end
    return result
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
