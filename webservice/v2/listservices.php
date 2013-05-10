<?php

// Is a callback function referenced?
$callback = isset($_GET['callback']) ? $_GET['callback'] : ( isset($_POST['callback']) ? $_POST['callback'] : false );

// Is there a callback?
if ( $callback !== false ) {
	echo $callback, '(';
}

?>{
	"services":[
		{
			"title":"RTÉ Radio 1 FM",
			"id":"radio1"
		},
		{
			"title":"RTÉ 2fm",
			"id":"2fm"
		},
		{
			"title":"RTÉ lyric fm",
			"id":"lyricfm"
		},
		{
			"title":"RTÉ Raidió na Gaeltachta",
			"id":"rnag"
		},
		{
			"title":"RTÉ Gold",
			"id":"gold"
		},
		{
			"title":"RTÉ 2XM",
			"id":"2xm"
		},
		{
			"title":"RTÉ Choice",
			"id":"choice"
		},
		{
			"title":"RTÉ Junior/Chill",
			"id":"junior-chill"
		},
		{
			"title":"RTÉ Pulse",
			"id":"pulse"
		},
		{
			"title":"RTÉ Radio 1 extra",
			"id":"radio1extra"
		},
		{
			"title":"RTÉ Radio 1 LW",
			"id":"radio1lw"
		},
		{
			"title":"RTE ONE [TV]",
			"id":"tvone"
		},
		{
			"title":"RTE TWO [TV]",
			"id":"tvtwo"
		},
		{
			"title":"BBC Radio 4",
			"id":"bbcradio4"
		},
		{
			"title":"BBC Radio 5",
			"id":"bbcradio5"
		},
		{
			"title":"BBC Radio Ulster",
			"id":"bbcradioulster"
		},
		{
			"title":"BBC World Service",
			"id":"bbcworldservice"
		},
		{
			"title":"BBC News 24 [TV]",
			"id":"bbcnews24"
		},
		{
			"title":"Dail",
			"id":"dail"
		},
		{
			"title":"Seanad",
			"id":"seanad"
		},
		{
			"title":"Al Jazeera [TV]",
			"id":"aljazeera"
		},
		{
			"title":"CNN [TV]",
			"id":"cnn"
		},
		{
			"title":"Newstalk",
			"id":"newstalk"
		},
		{
			"title":"Sky News [TV]",
			"id":"skynews"
		},
		{
			"title":"Today fm",
			"id":"todayfm"
		},
		{
			"title":"WRN",
			"id":"npr"
		}
	]
}<?php

// Is there a callback?
if ( $callback !== false ) {
	echo ');';
}

?>
