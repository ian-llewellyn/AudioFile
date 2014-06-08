<?php

// Not sure if these are actually needed - seemed to be working ok without
ini_set('memory_limit', '-1');
set_time_limit(0);

// All dates and times are in UTC
date_default_timezone_set('UTC');

// Include Common configuration parameters
require_once('common-config.php');
require_once('functions.inc');

// Arguments we want to get and any defaults we want to set
// Service
$service = isset($_GET['service']) ? $_GET['service'] : ( isset($_POST['service']) ? $_POST['service'] : 'radio1' );
#log_message(4, 'Service: ' . $service);

// HTTP Headers
header('Content-Type: audio/mpeg');
#header('Content-Type: text/plain');
#header('Content-Disposition: attachment; filename=' . $file_title . $recording_suffix);
header('Transfer-coding: chunked');
#log_message(3, 'About to readfile_chunked()');

// Loop
while ( true ) {
	// What date is it now (UTC)
	#$start_date = date('Y-m-d H:i:s:00');
	$start_date = date('Y-m-d');
	// Find the latest file
	$dir_listing = scandir($rotter_base_dir . $service . '/' . $start_date);

	// Clear out any unwanted files ('.idx', '.', '..', etc.)
	$dir_listing = array_filter($dir_listing, "dir_listing_filter");

	$latest_file = array_pop($dir_listing);

	// Find out how much of it is written
	$handle = fopen($rotter_base_dir . $service . '/' . $start_date . '/' . $latest_file, 'r');
	fseek($handle, 0, SEEK_END);
	$current_length = ftell($handle);

	$delta_failures = 0;
	while ( $delta_failures <= 3 ) {
		// Wait a moment
		sleep(1);

		$last_length = $current_length;

		// How big is the file now?
		fseek($handle, 0, SEEK_END);
		$current_length = ftell($handle);

		$chunk_size = $current_length - $last_length;
		if ( $chunk_size <= 0 ) {
			$delta_failures++;
			continue;
		}
		$delta_failures = 0;

		// Rewind
		fseek($handle, $chunk_size * -1, SEEK_CUR);

		// Send the updates to the client
		echo fread($handle, $chunk_size);
		ob_flush();
	}
	fclose($handle);
}
?>
