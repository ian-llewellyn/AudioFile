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
    'defaultFormat':'mp3',
    'trackLengthDefault': 3600 // Seconds.
};

/* Track current player state. */
var playerState = {
    'station' : undefined,
    'stationName': undefined,
    'filename': undefined,
    'date': new Date(),
    'mediaUrl': undefined,
    'playDate': undefined,
    'state':'STOPPED',
    'elapsed': undefined,
    'playSpeed': 1,
    'volume': 1,
    'muted': false,
    'playlist': {},
    'playlistOffset': 0,
    'trackend': false
};

/* 
    Our constructor 
*/
function AudioPlayer(id){
	this.id = id;
    this.init();
}

/*
    Convert filename to data object.
*/
AudioPlayer.prototype.parseFileDate = function(filename) {
    filename = filename.replace('.mp3','');
    return moment.utc(filename,'YYYY-MM-DD-HH-mm-ss-SS').format()
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
            playerState.playlist = filelist;
            var listLength = filelist.files.length;
            var fileBlockID = '#filelist';
            $(fileBlockID).empty();
            for( var i = 0; i < listLength;  i++)
            {
                // Use ICH template to fill a file block.
                filelist.files[i].playlistOffset = i;
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
 * Play / Pause Events when button clicked.
*/
AudioPlayer.prototype.play = function() {
    if( $('.rte-icon-pause-1').length !== 0 )    
    {
        $('#playbutton').removeClass('rte-icon-pause-1'); 
        $('#playbutton').addClass('rte-icon-play-1');      
        $(player.id).jPlayer('pause');
        $('#playing_status').html('PAUSED');
        playerState.state = "PAUSED";
    }
    else if( $('.rte-icon-play-1').length !== 0 ) 
    {
        $('#playbutton').removeClass('rte-icon-play-1'); 
        $('#playbutton').addClass('rte-icon-pause-1');  
        $(player.id).jPlayer('play');
        $('#playing_status').html('PLAYING');
        playerState.state = "PLAYING";
    }
    else
    {
        $('#playbutton').removeClass('rte-icon-play-1');        
        $('#playbutton').removeClass('rte-icon-pause-1'); 
        $('#playbutton').addClass('rte-icon-play-1');
    }
};

/*
 * Skip forwards/backwards X number of seconds.
 * If we skip outside the current hour, load and play from that offset.
 */
AudioPlayer.prototype.skip = function(seconds){
    if(playerState.state == "PLAYING")
    {
        console.log('Elapsed: ' + playerState.elapsed);
        console.log('Skip: ' + seconds);
        console.log( parseInt(playerState.elapsed,10) + parseInt(seconds,10) );

        var newTime = parseInt(playerState.elapsed,10) + parseInt(seconds,10);

        // It would be nice to skip back to the previous hour instead - offset.
        if(newTime < 0){
            newTime = 0;
        }

        // We should skip ahead to next hour + offset.
        if(newTime >= 3600){
            newTime = 3600;
        }

        $(this.id).jPlayer("play", newTime );
    }
};

/*
 * Change play speed by 0.5x steps. 
 * Range is between 0.5 to 4x 
 */
AudioPlayer.prototype.setPlaySpeed = function(speed){
    
    var newSpeed = parseFloat(playerState.playSpeed,10) + parseFloat(speed,10);

    // Reset the speed to 1
    if( parseFloat(speed,10) == 1)
    {
        newSpeed = 1;
    }
    else
    {
        // Ensure speed is between 0.5x and 4x
        if(newSpeed >= 4)
        { 
            newSpeed = 4; 
        }
        
        if(newSpeed <= 0.5)
        {
            newSpeed = 0.5;
        }
    }

    console.log(newSpeed);
    if(playerState.state == "PLAYING")
    {
        $(this.id).jPlayer('playbackRate', parseFloat(newSpeed,10));
        $('#speed').html(newSpeed + 'x');
        playerState.playSpeed = newSpeed;
    }
};

/*
 * Mute the player if not already muted.
 */
AudioPlayer.prototype.toggleMute = function(){
    if(playerState.muted)
    {
        // If we are muted, reset to previous volume.
        $(this.id).jPlayer('volume', parseFloat( playerState.volume, 10));
        $('#volume').html( parseInt(playerState.volume * 100, 10) + '%');
        playerState.muted = false;
    }
    else
    {
        // Set volume to 0, ie mute.
        $(this.id).jPlayer('volume', 0);
        $('#volume').html('MUTE');
        playerState.muted = true;
    }
};

/*
 * Change playback volume by 0.1 steps between 0 - 1.
 * Set the volume level on the display as a percentage.  
 */
AudioPlayer.prototype.adjustVolume = function(value){
    
    // Touching volume cancels mute.
    if(playerState.muted)
    {
        this.toggleMute();
    }

    var newVolume = parseFloat(playerState.volume,10) + parseFloat(value,10);
    
    if(newVolume >= 1)
    { 
        newVolume = 1; 
    }
    
    if(newVolume <= 0)
    {
        newVolume = 0;
    }
    
    $(this.id).jPlayer('volume', parseFloat(newVolume,10));

    $('#volume').html( parseInt(newVolume * 100, 10) + '%');
    playerState.volume = newVolume;
    
};

/* 
    Tune the Radio to the selected station.

    - If no date is selected, load the file list for today.
    - Otherwise grab the files for selected date. 
*/
AudioPlayer.prototype.setStation = function(stationid, name) {
    var calendarDate = $( "#datepicker" ).datepicker( "getDate" );
    playerState.station = stationid;
    playerState.stationName = name;
    this.getFileList(stationid, calendarDate );
    $('#station_name').html(playerState.stationName);
};

/* 
    Update the file list for a given date.

    - Only update if we already have a station.
*/
AudioPlayer.prototype.changeDate = function(date) {
    if(playerState.station !== undefined)
    {
        playerState.date = date;
        $('#play_date').html( moment.utc(playerState.date).format('DD/MM/YYYY') );
        this.getFileList(playerState.station, date );
    }
};


/*
    Load a file from the file list as the currently selected media. 
*/
AudioPlayer.prototype.selectFile = function(filename, playlistOffset) {
    playerState.playlistOffset = playlistOffset;
    playerState.filename = filename;
    playerState.mediaUrl = this.getFileUrl( playerDefaults.defaultFormat, playerState.station, playerState.date, filename);
    this.setMediaSource(playerState.mediaUrl);

    playerState.playDate = player.parseFileDate( playerState.filename );
    console.log(moment(playerState.playDate).format('HH:mm:ss'));
    $('#play_time').html( moment(playerState.playDate).format('HH:mm:ss') );
};

/*
    When a file finishs playing we need to advance to the next in our play list.
*/
AudioPlayer.prototype.advancePlaylist = function(playerObj){

    // Should be between 0 and max elements in playlist.
    // More than 24 means we need to advance a day.
    if(playerState.playlistOffset < playerState.playlist.files.length)
    {
        var filename = playerState.playlist.files[ playerState.playlistOffset + 1 ].file;
        console.log(filename);
        playerObj.selectFile(filename, playerState.playlistOffset + 1 );
        $(playerObj.id).jPlayer('play');
    }
    else
    {
        // Next Day.
        console.log('Next day');
    }
};

/*
 * Update the time elapsed on the display using the selected hour as an offset.
 * Event fires every ~250 ms.
 *
 */
AudioPlayer.prototype.updateTimer = function(event, player){
    if(playerState.state == 'PLAYING')
    {
        var currentTime = Math.floor(event.jPlayer.status.currentTime);
        playerState.elapsed = currentTime;
        var offset = moment(playerState.playDate).add('seconds', currentTime);
        $('#play_time').html( moment(offset).format('HH:mm:ss') );   

        // if(event.jPlayer.status.currentTime >= playerDefaults.trackLengthDefault - 1) 
        // {
        //     if(!playerState.trackend)
        //     {
        //         console.log("Track end.");
        //         player.advancePlaylist();
        //         playerState.trackend = true;
        //     }
        // } 
    }
};

/* 
    Init Method 
*/
AudioPlayer.prototype.init = function() {
    
    var playerObj = this;
    this.getServices(); // Load our stations.

    $(this.id).jPlayer( {
        ready: function () {
            
        }
    })
    .bind($.jPlayer.event.timeupdate, function(e){ playerObj.updateTimer(e, playerObj);      } )
    .bind($.jPlayer.event.seeking,    function(e){ $('#playing_status').html('BUFFERING..'); } )
    .bind($.jPlayer.event.seeked,     function(e){ $('#playing_status').html('PLAYING');     } )
    .bind($.jPlayer.event.error,      function(e){ console.log(e);                           } )
    .bind($.jPlayer.event.ended,      function(e){ playerObj.advancePlaylist(playerObj);     } )
    

    // Check cookies or url for params.

    // Set the default displayed date to today.
    $('#play_date').html( moment.utc(playerState.date).format('DD/MM/YYYY') );
};
