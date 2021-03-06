<?php

$files = array(
'2011-10-29-00-00-00-00.mp3',
'2011-10-29-01-00-00-01.mp3',
'2011-10-29-02-00-00-00.mp3',
'2011-10-29-03-00-00-00.mp3',
'2011-10-29-04-00-00-01.mp3',
'2011-10-29-05-00-00-02.mp3',
'2011-10-29-06-00-00-00.mp3',
'2011-10-29-07-00-00-02.mp3',
'2011-10-29-08-00-00-01.mp3',
'2011-10-29-09-00-00-02.mp3',
'2011-10-29-10-00-00-02.mp3',
'2011-10-29-11-00-00-02.mp3',
'2011-10-29-12-00-00-02.mp3',
'2011-10-29-13-00-00-02.mp3',
'2011-10-29-14-00-00-02.mp3',
'2011-10-29-15-00-00-01.mp3',
'2011-10-29-16-00-00-00.mp3',
'2011-10-29-17-00-00-01.mp3',
'2011-10-29-18-00-00-01.mp3',
'2011-10-29-19-00-00-02.mp3',
'2011-10-29-20-00-00-00.mp3',
'2011-10-29-21-00-00-00.mp3',
'2011-10-29-22-00-00-00.mp3',
'2011-10-29-23-00-00-00.mp3',
'2011-10-30-00-00-00-02.mp3',
'2011-10-30-01-00-00-00.mp3',
'2011-10-30-02-00-00-01.mp3',
'2011-10-30-03-00-00-01.mp3',
'2011-10-30-04-00-00-00.mp3',
'2011-10-30-05-00-00-00.mp3',
'2011-10-30-06-00-00-00.mp3',
'2011-10-30-07-00-00-00.mp3',
'2011-10-30-08-00-00-01.mp3',
'2011-10-30-09-00-00-00.mp3',
'2011-10-30-10-00-00-02.mp3',
'2011-10-30-11-00-00-01.mp3',
'2011-10-30-12-00-00-00.mp3',
'2011-10-30-13-00-00-00.mp3',
'2011-10-30-14-00-00-01.mp3',
'2011-10-30-15-00-00-01.mp3',
'2011-10-30-16-00-00-02.mp3',
'2011-10-30-17-00-00-02.mp3',
'2011-10-30-18-00-00-02.mp3',
'2011-10-30-19-00-00-01.mp3',
'2011-10-30-20-00-00-02.mp3',
'2011-10-30-21-00-00-00.mp3',
'2011-10-30-22-00-00-00.mp3',
'2011-10-30-23-00-00-01.mp3',
'2011-10-31-00-00-00-01.mp3',
'2011-10-31-01-00-00-02.mp3',
'2011-10-31-02-00-00-00.mp3',
'2011-10-31-03-00-00-01.mp3',
'2011-10-31-04-00-00-02.mp3',
'2011-10-31-05-00-00-02.mp3',
'2011-10-31-06-00-00-00.mp3',
'2011-10-31-07-00-00-00.mp3',
'2011-10-31-08-00-00-00.mp3',
'2011-10-31-09-00-00-01.mp3',
'2011-10-31-10-00-00-01.mp3',
'2011-10-31-11-00-00-02.mp3',
'2011-10-31-12-00-00-00.mp3',
'2011-10-31-13-00-00-00.mp3',
'2011-10-31-14-00-00-01.mp3',
'2011-10-31-15-00-00-02.mp3',
'2011-10-31-16-00-00-01.mp3',
'2011-10-31-17-00-00-00.mp3',
'2011-10-31-18-00-00-00.mp3',
'2011-10-31-19-00-00-02.mp3',
'2011-10-31-20-00-00-00.mp3',
'2011-10-31-21-00-00-01.mp3',
'2011-10-31-22-00-00-01.mp3',
'2011-10-31-23-00-00-00.mp3'
);

?>
<html>
	<head>
	<title>Test</title>
	<style type="text/css">
table {
	border: solid navy 1px
}
thead {
	font-weight: bold
}
td {
	border: solid silver 1px;
	padding: 0.1em
}
	</style>
	</head>
<body>
<table>
	<thead>
		<td>File:</td>
		<td>Unix Time:</td>
		<td>tm_isdst</td>
		<td>date('H:i:s e')</td>
	</thead>
<?php

foreach ( $files as $file ) {
	list($year, $month, $day, $hour, $minute, $second, $hundredth) = explode('-', $file);
	$hundredth = substr($hundredth, 0, 2);

	$unix_time = mktime( $hour, $minute, $second, $month, $day, $year, 0 );
	$is_dst = localtime( $unix_time, true );
	$is_dst = $is_dst['tm_isdst'];
	$date = date('Y-m-d H:i:s e', $unix_time);
	echo "	<tr>\n";
	echo "		<td>$file</td>
		<td>$unix_time</td>
		<td>$is_dst</td>
		<td>$date</td>\n";
	echo "	</tr>\n";
}

?>
</table>
</body>
</html>
