#!/usr/bin/php
<?php

// Time1 midday June 21st 2011 UTC
// Time2 midday December 21st 2011 UTC

$time1 = mktime(12, 0, 0, 6, 21, 2011, 0);
$time2 = mktime(12, 0, 0, 12, 21, 2011, 0);

$localtime1 = date('H:i:s e', $time1);
$localtime2 = date('H:i:s e', $time2);

echo "time1: [$time1]\tlocaltime1: [$localtime1]\n";
echo "time2: [$time2]\tlocaltime2: [$localtime2]\n";

var_dump(localtime($time1));
var_dump(localtime($time2));

?>
