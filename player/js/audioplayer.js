/******************************************************
 * AudioFile Player UI 
 * 
 * 
 *****************************************************/

/* Defaults that the player will use. */
var playerDefaults = {
	'startTrack': 'audio/sweet_dreams.mp3',
    'stationsUrl': 'http://audiofile.rte.ie/webservice/v3/listservices.php',
    'filelistUrl': 'http://audiofile.rte.ie/webservice/v3/listfiles.php',
    'downloadUrl': 'http://audiofile.rte.ie/audio/'
};


/* 
    Our constructor 
*/
function AudioPlayer(id){
	this.id = id;
    this.init();
}

/* 
    Init Method 
*/
AudioPlayer.prototype.init = function(){
    $(this.id).jPlayer( {
        ready: function () {
            // Check cookies or url for params.
        }
    });
};

/* 
    Get a list of stations from the web service 
*/
AudioPlayer.prototype.getStations = function(){
    $.ajax({
       type: 'GET',
        url: playerDefaults.stationsUrl,
        jsonpCallback: 'callback',
        contentType: "application/json",
        dataType: 'jsonp',
        success: function(data) {
           return data;
        },
        error: function(e) {
           console.log(e.message);
           alert("Could not get station list from web service.");
        }
    });
};


/* 
    Get all available files for a given service and date.
    - default service is radio1.
    - default date is today.
    - date accepted in YYYY-MM-DD string or Date object format.

    - returns file list object.
*/
AudioPlayer.prototype.getFileList = function(service, date){

    if(service === undefined || service.length === 0){ service = 'radio1' }
    if(date === undefined || date == ''){ date = new Date(); }

    // If we get a date object
    if(typeof date.getMonth === 'function'){
        date = moment.utc(date).format('YYYY-MM-DD');
    }

    var requestUrl = playerDefaults.filelistUrl + "?service=" + service + "&date=" + date;

    $.ajax({
       type: 'GET',
        url: requestUrl,
        jsonpCallback: 'callback',
        contentType: "application/json",
        dataType: 'jsonp',
        success: function(data) {
           return data;
        },
        error: function(e) {
           console.log(e.message);
           alert("Could not fetch file list from web service.");
        }
    });    
};


/* 
    Get a download url for an audio file based on given params.
*/
AudioPlayer.prototype.getFileUrl = function(format, service, date, file){

    // If we get a date object
    if(typeof date.getMonth === 'function'){
        date = moment.utc(date).format('YYYY-MM-DD');
    }

    return playerDefaults.downloadUrl + format + "/" + service + "/" + date + "/" + file;
};

/* Reset the audio player */
AudioPlayer.prototype.reset = function(){
	if(this.id){
		$(this.id).jPlayer( "clearMedia" );
	}
};

/* Set the media source for the player */
AudioPlayer.prototype.setMediaSource = function(url){
	if(this.id){
		$(this.id).jPlayer( "setMedia", { "mp3": url } );
	}
};

