-- Pandoc filter for make docs: a link to a local .md page becomes its
-- .html, its anchor kept. Links with a scheme are left alone
function Link(el)
  if not el.target:match("^%a[%w+.-]*:") then
    el.target = el.target:gsub("%.md$", ".html"):gsub("%.md#", ".html#")
  end
  return el
end
