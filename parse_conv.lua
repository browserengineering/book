package.path = package.path .. ";/opt/homebrew/Cellar/luarocks/3.11.0/share/lua/5.4/?.lua"
json = require('dkjson')

function Div(el)
   if el.classes[1] == 'inline-quiz' then
      return process_quiz(el)
   end
end

function process_quiz(el)
   -- expecting Div [ Para ..., BulletList [[Plain ...], ...], Para ...]
   -- check that everything looks good
   if el.content[1].tag ~= 'Para' then
      print('Expected paragraph at beginning of quiz block.')
      return
   end
   if el.content[2].tag ~= 'BulletList' then
      print('Expected bulleted list at middle of quiz block.')
      return
   end
   if el.content[3].tag ~= 'Para' then
      print('Expected paragraph at end of quiz block.')
      return
   end

   local prompt = pandoc.utils.stringify(el.content[1])
   local answer = pandoc.utils.stringify(el.content[2].content[1])
   local distractors = {}
   for i, v in ipairs({table.unpack(el.content[2].content, 2)}) do
      distractors[i] = pandoc.utils.stringify(v)
   end
   local context = pandoc.utils.stringify(el.content[3].content)

   local encoded = encode_mc(prompt, answer, distractors, context)

   return pandoc.Div(pandoc.Para(pandoc.Str('')),
                     pandoc.Attr('', {"quiz-placeholder"},
                                 {{"data-quiz-questions", encoded},
                                  {"data-quiz-name", "foobar"}}))
end

function encode_mc(question, answer, distractors, context)
   local q = { type = "MultipleChoice",
               prompt = { prompt = question,
                          distractors = distractors },
               answer = { answer = answer },
               context = context }

   return json.encode({ questions = { q } })
end

-- print(encode_mc("What is the answer", "42", {"what", "I don't understand"}, "where's the tea?"))
