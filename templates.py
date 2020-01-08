header = """\
<tr><th>Time</th><th>{}</th></tr>
"""

bin_template = """\
<tr class="bin">
<th class="time">{:02d}</th>
<td class="bin_data {}">
<p class="arr" style="width:{:d}%">{}</p>
<p class="dep" style="width:{:d}%">{}</p>
</td>
</tr>
"""

table_template = """\
<table>
<colgroup>
<col style="width:3em;"/><col/>
</colgroup>
{}
</table>
"""

page_template = """\
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Bristol Mayfly</title>
<link href="mayfly.css" rel="stylesheet"/>
</head>
<body>
<h1 id="title">Bristol Arrivals and Departures</h1>
<div id="mayfly_chart">
<input type="text" id="services"/>
<div id="key"><table>
<colgroup>
<col style="width:8em;"/><col style="width:8em;"/>
</colgroup>
<tr><td class="bin_data"><p class="arr">Arrivals</p></td>
<td class="bin_data"><p class="dep">Departures</p></td></tr>
</table></div>
{}
</div></body></html>
"""
