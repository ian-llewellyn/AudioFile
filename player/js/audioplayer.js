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
    'audioUrl': 'http://audiofile.rte.ie/audio/',
    'stations': undefined,
    'defaultFormat':'mp3'
};

/* Track current player state. */
var playerState = {
    'station' : 'radio1',
    'filename': undefined,
    'date': moment.utc().format('YYYY-MM-DD'),
    'mediaUrl': undefined
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
AudioPlayer.prototype.init = function() {
    
    this.getServices(); // Load our stations.

    $(this.id).jPlayer( {
        ready: function () {
            // Check cookies or url for params.
        }
    });
};

/* 
    Get a list of stations from the web service 
*/
AudioPlayer.prototype.getServices = function() {
    $.ajax({
       type: 'GET',
        url: playerDefaults.stationsUrl,
        jsonpCallback: 'callback',
        contentType: "application/json",
        dataType: 'jsonp',
        success: function(stations) {
            this.stations = stations;
            var serviceLength = stations.services.length;
            var carouselLength = 5; // 5 slides
            var carouselSlots = 6; // 6 slots in each slide
            var blockPrefix = "#stations_block_"; 
            var slotTemp = -1; // We want to start at 0, this will be incremented on run.
            // Loop all available services.
            for(var i = 0; i < serviceLength; i++)
            {
                // If we are at a slide boundary, advance to next slot.
                if( !(i % carouselSlots) )
                {
                    slotTemp++;
                }

                // Use ICH template to fill a station block.
                $(blockPrefix + slotTemp).append( ich.stationblock( stations.services[i] ) );
            }

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
        success: function(filelist) {
            var listLength = filelist.files.length;
            var fileBlockID = '#filelist';
            $(fileBlockID).empty();
            for( var i = 0; i < listLength;  i++)
            {
                // Use ICH template to fill a file block.
                $(fileBlockID).append( ich.fileblock( filelist.files[i] ) );
            }
        },
        error: function(e) {
           console.log(e.message);
           alert("Could not fetch file list from web service.");
        }
    });    
};


/* 
    Get a file url.
*/
AudioPlayer.prototype.getFileUrl = function(format, service, date, file){

    // If we get a date object
    try{
        if(typeof date.getMonth === 'function'){
            date = moment.utc(date).format('YYYY-MM-DD');
        }
    } catch(e){
        console.log(e);
    }

    return playerDefaults.audioUrl + format + "/" + service + "/" + date + "/" + file;
};

/* 
    Reset the audio player 
*/
AudioPlayer.prototype.reset = function(){
	if(this.id){
		$(this.id).jPlayer( "clearMedia" );
	}
};

/* 
    Set the media source for the player 
*/
AudioPlayer.prototype.setMediaSource = function(url){
	if(this.id){
		$(this.id).jPlayer( "setMedia", { "mp3": url } );
	}
};

/*
    Press Play
*/
AudioPlayer.prototype.play = function() {
    if( $('.rte-icon-pause-1').length !== 0 )    
    {
        $('#playbutton').removeClass('rte-icon-pause-1'); 
        $('#playbutton').addClass('rte-icon-play-1');      
        console.log("Pause media.");
    }
    else if( $('.rte-icon-play-1').length !== 0 ) 
    {
        $('#playbutton').removeClass('rte-icon-play-1'); 
        $('#playbutton').addClass('rte-icon-pause-1');  
        console.log("Play media");
    }
    else
    {
        $('#playbutton').removeClass('rte-icon-play-1');        
        $('#playbutton').removeClass('rte-icon-pause-1'); 
        $('#playbutton').addClass('rte-icon-play-1');
    }
};

/* 
    Tune the Radio to the selected station.

    - If no date is selected, load the file list for today.
    - Otherwise grab the files for selected date. 
*/
AudioPlayer.prototype.setStation = function(stationid) {
    var calendarDate = $( "#datepicker" ).datepicker( "getDate" );
    playerState.station = stationid;
    this.getFileList(stationid, calendarDate );
};


/* 
    Update the file list for a given date.

    - Only update if we already have a station.
*/
AudioPlayer.prototype.changeDate = function(date) {
    if(playerState.station !== undefined)
    {
        playerState.date = date;
        this.getFileList(playerState.station, date );
    }
};


/*
    Load a file from the file list as the currently selected media. 
*/
AudioPlayer.prototype.selectFile = function(filename) {
    playerState.file = filename;
    playerState.mediaUrl = this.getFileUrl( playerDefaults.defaultFormat, playerState.station, playerState.date, filename);
    this.setMediaSource(playerState.mediaUrl);
};