header = """\
<tr><th colspan="2">{}</th></tr>
"""

bin_template = """\
<tr id="{bin_id}" class="bin">
<th class="time"><span>{bin_start_time}</span></th>
<td class="bin_data {heat}">
<p class="arr" style="width:{arrivals_width}">{arrivals_count}</p>
<div class="arr_svc hidden">{arrivals_listing}</div>
<p class="dep" style="width:{departures_width}">{departures_count}</p>
<div class="dep_svc hidden">{departures_listing}</div>
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
<script>var lookup = {};</script>
<script src="mayfly.js"></script>
</head>
<body>
<h1 id="title">Bristol Mayfly</h1>
<p id="updated">{}</p>
<div id="mayfly_chart">
<input type="text" id="services" placeholder="Enter flight numbers here"/>
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

service_list_template = """\
<ul>{}</ul>
"""

ezy_service_template = """\
<li class="ezy"><span class="time">{time}</span>:
<span class="service">{operator_id}{service_id} {dest_or_orig}</span>
<span class="{late_str}">{delay_str}</span></li>
"""

nonezy_service_template = """\
<li class="nonezy"><span class="time">{time}</span>:
<span class="service">{operator_id}{service_id} {dest_or_orig}</span></li>
"""
