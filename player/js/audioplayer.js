/******************************************************
 * AudioFile Player UI 
 * 
 * 
 *****************************************************/

/* Get a named parameter that may have been passed in the URL string */
function getParameterByName(name) {
    name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results == null ? undefined : decodeURIComponent(results[1].replace(/\+/g, " "));
}


/* Defaults that the player will use. */
var playerDefaults = {
	'startTrack': 'audio/sweet_dreams.mp3',
    'stationsUrl': 'http://audiofile.rte.ie/webservice/v3/listservices.php',
    'filelistUrl': 'http://audiofile.rte.ie/webservice/v3/listfiles.php',
    'audioUrl': 'http://audiofile.rte.ie/audio/',
    'stations': undefined,
    'defaultFormat':'mp3',
    'trackLengthDefault': 3600, // Seconds.
    'preload': undefined
};

/* Track current player state. */
var playerState = {
    'station' : undefined,
    'stationName': undefined,
    'filename': undefined,
    'date': new Date(),         // Date selected by cal widget.
    'mediaUrl': undefined,
    'playDate': undefined,      // Current date we are playing.
    'state':'STOPPED',
    'elapsed': undefined,
    'playSpeed': 1,
    'volume': 1,
    'muted': false,
    'playlist': {},
    'playlistOffset': 0,
    'markstart': undefined,
    'markend': undefined,
    'callbacks':undefined
};

/* 
    Our constructor 
*/
function AudioPlayer(id){
	this.id = id;
    this.init();
}

/*
    Load Params from URL string if available
    - Return false if no valid params can be parse.
    - Return object with at least a valid stationid and start timestamp.
      stop timestamp is undefined if unavailable or could not be parsed.
*/
AudioPlayer.prototype.checkParams = function(){

    // We need these three to play
    var start   = getParameterByName('start');
    var service = getParameterByName('service');
    var stop    = getParameterByName('stop');

    if(start !== undefined && service !== undefined){

        // Valid start timestamp (required field)
        var parsedStart = moment(start, "YYYY-MM-DD-HH-mm-ss", true).isValid();
        if(!parsedStart){   return false;   }
        parsedStart = moment(start, "YYYY-MM-DD-HH-mm-ss").toDate();
        
        // If start date is in the future (ie greater than new Date())
        if( moment.utc(parsedStart).isAfter( new Date() ) ){
            alert("Parameter start is greater than current time.");
            return false;
        }
        
        // Parse stop timestamp if valid. Leave undefined otherwise as it is not strictly needed. 
        var parsedStop = moment(stop, "YYYY-MM-DD-HH-mm-ss", true).isValid();
        if(!parsedStop){    
            parsedStop = undefined;
        }
        else{
            parsedStop = moment(stop, "YYYY-MM-DD-HH-mm-ss").toDate();
        }

        // Found station.
        return { 
            'stationid' : service,
            'start'     : parsedStart,
            'stop'      : parsedStop
        };
    }
    else{
        return false;
    }
};

/*
    Play an audio clip specified by params
*/
AudioPlayer.prototype.playClip = function(start, end, stationId, date){

};

/*
    Mark the current player time for clip download.
    - position can either be 'start' or 'end' 
*/
AudioPlayer.prototype.mark = function(position){
    var time = moment(playerState.playDate).add('seconds', playerState.elapsed).toDate();
    var formatted = moment(time).format('HH:mm:ss DD/MM/YYYY');
    if(position == 'start')
    {
        if( playerState.markend !== undefined && moment(playerState.markend).isBefore( time ) )
        {
            alert("Start position must be before end mark.");
        }
        else
        {
            playerState.markstart = time;
            $('#start-point').html('Start: ' + formatted);
        }
    }
    else if(position == 'end')
    {
        if(playerState.markstart == undefined || moment(playerState.markstart).isAfter( time ) )
        {
            alert("Start position must be before end mark.");
        }
        else
        {
            playerState.markend = time;
            $('#end-point').html('End: ' + formatted);
        }
    }
};


/*
    Download an audio file with given start and end times.
*/
AudioPlayer.prototype.download = function(){
    if(playerState.markstart === undefined || playerState.markend === undefined)
    {
        alert("Please mark the start and end positions of the required clip first.");
    }
    else if( moment(playerState.markstart).isAfter( playerState.markend ) )
    {
        // Should never happen.
        alert("End position cannot be before start.");
        playerState.markstart = undefined;
        playerState.markend = undefined;
        $('#start-point').empty();
        $('#end-point').empty();
    }
    else if( moment(playerState.markstart).isBefore( playerState.markend ) )
    {
        // Download.
        console.log("Download");

        // Should we remove markers after download clicked?
        playerState.markstart = undefined;
        playerState.markend = undefined;
        $('#start-point').empty();
        $('#end-point').empty();
    }

};

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
    var playerObj = this;
    $.ajax({
       type: 'GET',
        url: playerDefaults.stationsUrl,
        jsonpCallback: 'callback',
        contentType: "application/json",
        dataType: 'jsonp',
        success: function(stations) {
            playerDefaults.stations = stations;
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
            playerObj.setStation('radio1','RTÉ Radio 1 FM'); // RTE Radio 1 is our default.  
            playerState.callbacks.fire('stationsLoaded', playerObj);
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

    - autoplay: Automatically play first file in the returned list.
        - fileOffset: If using autoplay, which file should we autoplay
        - skip: If using autoplay, skip X seconds ahead. 
*/
AudioPlayer.prototype.getFileList = function(service, date, autoplay, fileOffset, skip){
    if(service === undefined || service.length === 0){ service = 'radio1' }
    if(date === undefined || date == ''){ date = new Date(); }

    // If we get a date object
    if(typeof date.getMonth === 'function'){
        date = moment.utc(date).format('YYYY-MM-DD');
    }

    var requestUrl = playerDefaults.filelistUrl + "?service=" + service + "&date=" + date;
    var playerObj = this;
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

            // Handle autoplay function (need one file or more.)
            if(autoplay && ( listLength >= 1) ){
                playerObj.selectFile(filelist.files[ fileOffset ].file, fileOffset);
                $(playerObj.id).jPlayer('play', skip);
            }

            for( var i = 0; i < listLength;  i++)
            {
                // Use ICH template to fill a file block.
                filelist.files[i].playlistOffset = i;
                $(fileBlockID).append( ich.fileblock( filelist.files[i] ) );
            }
            playerState.callbacks.fire('filesLoaded', playerObj);
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
        $(player.id).jPlayer('pause');
        playerState.state = "PAUSED";
    }
    else if( $('.rte-icon-play-1').length !== 0 ) 
    {
        $(player.id).jPlayer('play');
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
    if(stationid != playerState.station || playerState.station == undefined)
    {
        var calendarDate = $( "#datepicker" ).datepicker( "getDate" );
        playerState.station = stationid;
        playerState.stationName = name;

        // We need to be able to switch stations while continuing from the same point in time.
        if(playerState.state == 'PLAYING')
        {
            this.getFileList(stationid, calendarDate, true, playerState.playlistOffset, playerState.elapsed);
        }
        else
        {
            this.getFileList(stationid, calendarDate, false, false, false);
        }

        $('#station_name').html(playerState.stationName);
    }
};

/* 
    Update the file list for a given date.

    - Only update if we already have a station.
    - autoplay : start playing the first file on that date automatically.
*/
AudioPlayer.prototype.changeDate = function(date, autoplay) {

    playerState.date = date;
    playerState.playDate = date;
    $('#play_date').html( moment.utc(playerState.date).format('DD/MM/YYYY') );

    if(playerState.station !== undefined)
    {
        this.getFileList(playerState.station, date, autoplay, 0, 0 );
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
    $('#play_time').html( moment(playerState.playDate).format('HH:mm:ss') );
    $(this.id).jPlayer('play');

    // Highlight selected hour.
    $('.hourblocks').removeClass('navactive');
    $('#hourblock_' + playlistOffset).addClass('navactive');
};

/*
    When a file finishs playing we need to advance to the next in our play list.
    Offset lets us start the next or previous day with a given offset.
*/
AudioPlayer.prototype.advancePlaylist = function(playerObj, offset){
    var startTime = parseInt(playerState.elapsed,10) + parseInt(offset,10);
    playerState.playlistOffset = playerState.playlistOffset + 1;
    var nextDay = moment(playerState.playDate).add('days', 1);

    // Should be between 0 and max elements in playlist.
    // More than 24 means we need to advance a day.
    if(playerState.playlistOffset < 24)
    {
        var filename = playerState.playlist.files[ playerState.playlistOffset].file;
        playerObj.selectFile(filename, playerState.playlistOffset);
        if(playerState.state != 'PLAYING')
        {
            $(playerObj.id).jPlayer('play', startTime);
        }
    }
    else
    {
        /***** HERE BE DRAGONS *****/
        // We need to advance to the next day but we also need to be sure that
        // DST doesn't screw us over. Need to come back and test this. 
        if( moment(nextDay).isSame( new Date(), 'day' ) )
        {
            // If the next day is today, play the previous file. 
            var filename = playerState.playlist.files[ playerState.playlistOffset - 1].file;
            playerObj.selectFile(filename, playerState.playlistOffset - 1);
            if(playerState.state != 'PLAYING')
            {
                $(playerObj.id).jPlayer('play', startTime);
            }

        }
        else if( moment(nextDay).isAfter( new Date(), 'day' ) )
        {
            // If the next day is after today.
            alert("No further programs are available.");
        }
        else
        {
            // Otherwise advance to the next day.
            $("#datepicker").datepicker("setDate", moment(nextDay).format('DD/MM/YYYY') );
            this.changeDate( moment(nextDay).toDate(), true );
        }

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
    }
};



/* 
    Init Method 
*/
AudioPlayer.prototype.init = function() {
    var playerObj = this;
    playerState.callbacks = $.Callbacks();

    /* Check for params that we can use to init the player */
    var preload = this.checkParams();
    if(preload){
        playerState.preload = preload;
        console.log('preload');

        playerState.station = preload.stationid;
        playerState.date = preload.start;
        playerState.playDate = preload.start;

        $('#play_date').html( moment.utc( preload.start ).format('DD/MM/YYYY') ); 

        $("#datepicker").datepicker("setDate", moment.utc(playerState.preload.start).toDate() );
        playerState.markstart = preload.start;
        $('#start-point').html('Start: ' + moment(preload.start).format('HH:mm:ss DD/MM/YYYY') );

        if(preload.stop !== undefined){
        playerState.markend = preload.end;
            $('#end-point').html('End: ' + moment(preload.stop).format('HH:mm:ss DD/MM/YYYY') );
        }

        var onLoadPlay = function(event,playerObj){
            console.log(event);
            if(event == "stationsLoaded"){
                /*
                    Assuming that the file array remains in index == hour order.
                    TODO: Test this works with UTC and DST
                */
                var stationArray = playerDefaults.stations.services;
                for(var i = 0; i < stationArray.length; i++){

                    if(stationArray[i].id == preload.stationid){
                        playerState.stationName = stationArray[i].title;
                        $('#station_name').html(playerState.stationName);
                        break;
                    }
                }

                var fileOffset  = moment.utc(playerState.preload.start).hour();
                var minutes     = moment.utc(playerState.preload.start).minute();
                var seconds     = moment.utc(playerState.preload.start).second();
                var skip        = seconds + (minutes * 60);
                playerObj.getFileList(preload.stationid, preload.start, true, fileOffset, skip);
            }            
            if(event == "filesLoaded"){
                console.log("filesLoaded event");
                playerState.callbacks.remove(this);
            }
        };

        playerState.callbacks.add(onLoadPlay);
    } 

    this.getServices(); // Load our stations.
    $(this.id).jPlayer( {
        ready: function () {
           // Any post init for jPlayer. 
        }
    })
    .bind($.jPlayer.event.timeupdate, function(e){ playerObj.updateTimer(e, playerObj);      } )
    .bind($.jPlayer.event.seeking,    function(e){ $('#playing_status').html('BUFFERING..'); } )
    .bind($.jPlayer.event.seeked,     function(e){ $('#playing_status').html('PLAYING');     } )
    .bind($.jPlayer.event.stalled,    function(e){ $('#playing_status').html('BUFFERING.'); } )
    .bind($.jPlayer.event.play,       function(e){ 
        
        $('#playing_status').html('PLAYING');
        $('#playbutton').removeClass('rte-icon-play-1'); 
        $('#playbutton').addClass('rte-icon-pause-1'); 
        playerState.state = "PLAYING";
    })
    .bind($.jPlayer.event.pause,      function(e){ 

        $('#playing_status').html('PAUSED'); 
        $('#playbutton').removeClass('rte-icon-pause-1'); 
        $('#playbutton').addClass('rte-icon-play-1');  
        playerState.state = "PAUSED"; 

    })
    .bind($.jPlayer.event.ended,      function(e){ 
        playerState.elapsed = 0;
        playerObj.advancePlaylist(playerObj,0);     

    })
    .bind($.jPlayer.event.error + ".AudioPlayer", function(event) 
    { 
        if( event.jPlayer.error.type == 'e_url')
        {
            alert("This program is currently unavailable.");
            playerObj.advancePlaylist(playerObj, 0); 
        }
        console.log("Error Event: type = " + event.jPlayer.error.type); 
    });

    // Set the default displayed date to today.
    $('#play_date').html( moment.utc(playerState.date).format('DD/MM/YYYY') );
};
