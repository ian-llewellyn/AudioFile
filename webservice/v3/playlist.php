<?php
// Include the common configuration parameters
require_once('common-config.php');

// Parse the service from the GET or POST variables
$service = isset($_GET['service']) ? $_GET['service'] : ( isset($_POST['service']) ? $_POST['service'] : false );

// Parse the date from the GET or POST variables
$date = isset($_GET['date']) ? $_GET['date'] : ( isset($_POST['date']) ? $_POST['date'] : false );

if ( $service === false || $date === false ) {
?>
<!DOCTYPE html5>
<html>
  <head>
    <title>AudioFile Playlist Generator</title>
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  </head>
  <body>
    <form action="" method="get">
      <input type="date">
    </form>
  </body>
</html>
<?php
	die();
}

// Does the requested date exist?
if ( !is_dir($rotter_base_dir . $service . '/' . $date) ) {
        // Produce an empty array
        $dir_listing = array();
} elseif ( ($dir_listing = scandir($rotter_base_dir . $service . '/' . $date)) === FALSE) {
        $dir_listing = array();
}

// Loop through and only keep the relevant audio files
$i = 0;
while ( $i < count($dir_listing) ) {
        if ( preg_match('/^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}' . $recording_suffix . '$/', $dir_listing[$i]) != 1 ) {
                array_splice($dir_listing, $i, 1);
        } else {
                $i++;
        }
}

header('Content-type: audio/x-scpls');

echo "[playlist]\n";

$i = 0;
foreach ( $dir_listing as $file ) {
	$i++;
	$url = "http://audiofile.rte.ie/audio/$format/$service/$date/$file";
	echo "File$i=$url\n";
	echo "Title$i=$service $file\n";
	#LengthX : Length in seconds of track. Value of -1 indicates indefinite (streaming).
}

echo "NumberOfEntries=$i\n";
echo "Version=2\n";

?>
