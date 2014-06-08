<?php
/*
 * Created on Oct 20, 2010
 *
 * To change the template for this generated file go to
 * Window - Preferences - PHPeclipse - PHP - Code Templates
 */

// Logging function
function log_message($msg_level, $msg, $bare_log = false) {
	global $log_level, $log_file;

	// Should this go any further
	if ($log_level < $msg_level) return true;
	// open file
	#$fd = fopen(dirname($_SERVER['SCRIPT_FILENAME']) . '/download.log', 'a');
	$fd = fopen($log_file, 'a');
	if (!$fd) return false;
	// append date/time to message
	$str = ($bare_log === false ? '[' . date('Y/m/d H:i:s T', mktime()) . '] ' . $_SERVER['REMOTE_ADDR'] . ' [' . $msg_level . '] ' : '') . $msg;
	// write string
	if (fwrite($fd, $str . "\n") === false) return false;
	// close file
	fclose($fd);
	return true;
}

// Include Common configuration parameters
require_once('common-config.php');

/**
 * dir_listing_filter - returns true only if file is an audio file that we care about
 */
function dir_listing_filter($file) {
	global $recording_suffix;
	log_message(5, 'dir_listing_filter($file = \'' . $file . '\')');

	$pmatch = '/^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}'. $recording_suffix .'/';
	if ( preg_match($pmatch, $file) != 1 ) {
		return false;
	} else {
		return true;
	}
}

/* For an end date_time that corresponds to a filename,
 * should the editspec for mpgedit be: -e - ?
 *
 * Also, I need to check if there is a way to determine the length of a file quickly so that
 * missing patches can be detected and replaced with silence.
 */
function get_filename_for_date_time($date_time, $is_end = false) {
	global $rotter_base_dir, $service, $recording_suffix;
	log_message(4, 'get_filename_for_date_time($date_time = \'' . $date_time . '\', $is_end = \'' . $is_end . '\')');

	// Get the date out of date_time
	preg_match('/^((\d{4})-(\d{2})-(\d{2}))[ -]((\d{2})[:-](\d{2})[:-](\d{2})[.-](\d{2}))$/', $date_time, $matches);
	list(, $date, $yr, $mo, $dy, $time, $hr, $mi, $se, $hs) = $matches;

	// List the directory for date_time
	$dir_listing = scandir($rotter_base_dir . $service . '/' . $date);

	// Get date_time - 1 day
	$day_before_date_time = strftime("%Y-%m-%d", gmmktime(0, 0, 0, $mo, $dy-1, $yr));

	// Is there a directory for yesterday?
	if ( is_dir($rotter_base_dir . $service . '/' . $day_before_date_time) ) {
		// Get yesterday's directory listing if it exists
		$yday_dir_listing = scandir($rotter_base_dir . $service . '/' . $day_before_date_time);

		// Add yesterday's directory listing too if it exists
		if ( $yday_dir_listing !== false ) $dir_listing = array_merge($dir_listing, $yday_dir_listing);
	}

	// Clear out any unwanted files ('.idx', '.', '..', etc.)
	$dir_listing = array_filter($dir_listing, "dir_listing_filter");

	// Insert our date_time as a fake file into the directory listing
	$fake_file = str_replace(array(' ', ':', '.'), '-', $date_time) . $recording_suffix;
	$dir_listing[] = $fake_file;

	// Reverse sort the array so that index + 1 will be the file we want
	rsort($dir_listing);

	// The most likely candidate
	$file = $dir_listing[array_search($fake_file, $dir_listing)+1];

	// If is_end is set and the timestamp of the file is the same as that of the fake file, we want the next earliest file
	if ( $file == $date_time.$recording_suffix && $is_end === true ) {
		$file = $dir_listing[array_search($fake_file, $dir_listing)+2];
	}

	return $file;
}

/* Find any files recorded between the end of file_a and the start of file_y
 */
function get_intermediate_files($file_a, $file_y) {
	global $rotter_base_dir, $service, $recording_suffix;
	log_message(4, 'get_intermediate_files($file_a = \'' . $file_a . '\', $file_b = \'' . $file_y . '\')');

	preg_match('/^((\d{4})-(\d{2})-(\d{2}))[ -]((\d{2})[:-](\d{2})[:-](\d{2})[.-](\d{2}))' . $recording_suffix . '$/', $file_a, $matches);
	list(, $start_date, $start_yr, $start_mo, $start_dy, $start_time, $start_hr, $start_mi, $start_se, $start_hs) = $matches;

	preg_match('/^((\d{4})-(\d{2})-(\d{2}))[ -]((\d{2})[:-](\d{2})[:-](\d{2})[.-](\d{2}))' . $recording_suffix . '$/', $file_y, $matches);
	list(, $end_date, $end_yr, $end_mo, $end_dy, $end_time, $end_hr, $end_mi, $end_se, $end_hs) = $matches;

	// Scan the relavant directory / directories
	$dir_listing = scandir("$rotter_base_dir/$service/$start_date");
	if ( $start_date != $end_date ) $dir_listing = array_merge($dir_listing, scandir("$rotter_base_dir/$service/$end_date"));

	// Clear out any unwanted files ('.idx', '.', '..', etc.)
	$dir_listing = array_filter($dir_listing, "dir_listing_filter");

	rsort($dir_listing);
	$index = count($dir_listing)-1;
	while ( $dir_listing[$index] != $file_a ) {
		array_pop($dir_listing);
		$index--;
	}
	array_pop($dir_listing);

	sort($dir_listing);
	$index = count($dir_listing)-1;
	while ( $dir_listing[$index] != $file_y ) {
		array_pop($dir_listing);
		$index--;
	}
	array_pop($dir_listing);

	return $dir_listing;
}

function get_time_diff($date_time1, $date_time2) {
	// Accepts date_times in the form:
	// YYYY-MM-DD-HH-mm-ss-hh or
	// YYYY-MM-DD HH:mm:ss.hh
	log_message(4, 'get_time_diff($date_time1 = \'' . $date_time1 . '\', $date_time2 = \'' . $date_time2 . '\')');

	preg_match('/^(\d{4})-(\d{2})-(\d{2})[ -](\d{2})[:-](\d{2})[:-](\d{2})[.-](\d{2})$/', $date_time1, $matches);
	list(, $yr, $mo, $dy, $hr, $mi, $se, $hs) = $matches;
	$days1 = gregoriantojd($mo, $dy, $yr);
	$time1 = floatval(intval($hr)*3600 + intval($mi)*60 + intval($se) . '.' . $hs);

	preg_match('/^(\d{4})-(\d{2})-(\d{2})[ -](\d{2})[:-](\d{2})[:-](\d{2})[.-](\d{2})$/', $date_time2, $matches);
	list(, $yr, $mo, $dy, $hr, $mi, $se, $hs) = $matches;
	$days2 = gregoriantojd($mo, $dy, $yr);
	$time2 = floatval(intval($hr)*3600 + intval($mi)*60 + intval($se) . '.' . $hs);

	$days_diff = $days2 - $days1;
	$time_diff = $time2 - $time1;

	return round($days_diff*3600*24 + $time_diff, 2);
}

function readfile_chunked($filename, $retbytes=true) {
	// $chunksize = 0.25*(1024*1024); // how many bytes per chunk
	$chunksize = 1024; // how many bytes per chunk
	//$chunksize = 0.25*(1024*1024);
	$buffer = '';
	$cnt = 0;
	// $handle = fopen($filename, 'rb');
	$handle = $filename;
	if ($handle === false) {
		return false;
	}
	while (!feof($handle)) {
		$buffer = fread($handle, $chunksize);
		echo $buffer;
		ob_flush();
		flush();
		if ($retbytes) {
			$cnt += strlen($buffer);
		}
	}
	// $status = fclose($handle);
	$status = true;
	if ($retbytes && $status) {
		return $cnt; // return num. bytes delivered like readfile() does.
	}
	return $status;
}
?>
