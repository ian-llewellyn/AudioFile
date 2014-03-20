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
			"id":"radio1",
			"image_url":"http://audiofile.rte.ie/images/radio1.png"
		},
		{
			"title":"RTÉ 2fm",
			"id":"2fm",
			"image_url":"http://audiofile.rte.ie/images/2fm.png"
		},
		{
			"title":"RTÉ lyric fm",
			"id":"lyricfm",
			"image_url":"http://audiofile.rte.ie/images/lyricfm.png"
		},
		{
			"title":"RTÉ Raidió na Gaeltachta",
			"id":"rnag",
			"image_url":"http://audiofile.rte.ie/images/rnag.png"
		},
		{
			"title":"RTÉ Gold",
			"id":"gold",
			"image_url":"http://audiofile.rte.ie/images/gold.png"
		},
		{
			"title":"RTÉ 2XM",
			"id":"2xm",
			"image_url":"http://audiofile.rte.ie/images/2xm.png"
		},
		{
			"title":"RTÉ Junior/Chill",
			"id":"junior-chill",
			"image_url":"http://audiofile.rte.ie/images/junior-chill.png"
		},
		{
			"title":"RTÉ Pulse",
			"id":"pulse",
			"image_url":"http://audiofile.rte.ie/images/pulse.png"
		},
		{
			"title":"RTÉ Radio 1 extra",
			"id":"radio1extra",
			"image_url":"http://audiofile.rte.ie/images/radio1extra.png"
		},
		{
			"title":"RTÉ Radio 1 LW",
			"id":"radio1lw",
			"image_url":"http://audiofile.rte.ie/images/radio1lw.png"
		},
		{
			"title":"RTE ONE [TV]",
			"id":"tvone",
			"image_url":"http://audiofile.rte.ie/images/tvone.png"
		},
		{
			"title":"RTE TWO [TV]",
			"id":"tvtwo",
			"image_url":"http://audiofile.rte.ie/images/tvtwo.png"
		},
		{
			"title":"BBC Radio 4",
			"id":"bbcradio4",
			"image_url":"http://audiofile.rte.ie/images/bbcradio4.png"
		},
		{
			"title":"BBC Radio 5",
			"id":"bbcradio5",
			"image_url":"http://audiofile.rte.ie/images/bbcradio5.png"
		},
		{
			"title":"BBC Radio Ulster",
			"id":"bbcradioulster",
			"image_url":"http://audiofile.rte.ie/images/bbcradioulster.png"
		},
		{
			"title":"BBC World Service",
			"id":"bbcworldservice",
			"image_url":"http://audiofile.rte.ie/images/bbcworldservice.png"
		},
		{
			"title":"BBC News 24 [TV]",
			"id":"bbcnews24",
			"image_url":"http://audiofile.rte.ie/images/bbcnews24.png"
		},
		{
			"title":"Dail",
			"id":"dail",
			"image_url":"http://audiofile.rte.ie/images/dail.png"
		},
		{
			"title":"Seanad",
			"id":"seanad",
			"image_url":"http://audiofile.rte.ie/images/seanad.png"
		},
		{
			"title":"Al Jazeera [TV]",
			"id":"aljazeera",
			"image_url":"http://audiofile.rte.ie/images/aljazeera.png"
		},
		{
			"title":"CNN [TV]",
			"id":"cnn",
			"image_url":"http://audiofile.rte.ie/images/cnn.png"
		},
		{
			"title":"Newstalk",
			"id":"newstalk",
			"image_url":"http://audiofile.rte.ie/images/newstalk.png"
		},
		{
			"title":"Sky News [TV]",
			"id":"skynews",
			"image_url":"http://audiofile.rte.ie/images/skynews.png"
		},
		{
			"title":"Today fm",
			"id":"todayfm",
			"image_url":"http://audiofile.rte.ie/images/todayfm.png"
		},
		{
			"title":"WRN",
			"id":"npr",
			"image_url":"http://audiofile.rte.ie/images/wrn.png"
		}
	]
}<?php

// Is there a callback?
if ( $callback !== false ) {
	echo ');';
}

?>
