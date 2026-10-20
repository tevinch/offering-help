split("\n")
| map(if test("^[ \t\r]*//") then "" else . end)
| join("\n")
| fromjson
