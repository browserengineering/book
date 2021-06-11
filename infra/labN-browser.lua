function dump(o)
   if type(o) == 'table' then
      local s = '{ '
      for k,v in pairs(o) do
         if type(k) ~= 'number' then k = '"'..k..'"' end
         s = s .. '['..k..'] = ' .. dump(v) .. ','
      end
      return s .. '} '
   else
      return tostring(o)
   end
end

function Meta(meta)
  for k, v in pairs(meta.chapters) do
    if v.lab and v.lab[1].text == ("lab" .. tostring(meta.chapter) .. ".py") then
      meta.name = string.gsub(k, "%.md", "")
    end
  end
  return meta
end

