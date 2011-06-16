package clipper
{
	import mx.core.UIComponent;
	
	import org.osmf.containers.MediaContainer;
	import org.osmf.elements.AudioElement;
	import org.osmf.events.TimeEvent;
	import org.osmf.media.MediaPlayer;
	import org.osmf.media.URLResource;
	
	public class AudioSprite extends UIComponent
	{
		public function AudioSprite()
		{
			super();
		}
		
		override protected function createChildren():void {
			mediaPlayer = new MediaPlayer();
			
			mediaPlayer.volume = .5;
			mediaPlayer.loop = true;
			mediaPlayer.addEventListener(TimeEvent.CURRENT_TIME_CHANGE, onTimeUpdated);        
			mediaPlayer.addEventListener(TimeEvent.DURATION_CHANGE, onTimeUpdated);
			mediaPlayer.autoPlay = true;
		}
		
		public function setSound(url:String):void {
			var audioElement:AudioElement = new AudioElement();
			audioElement.resource = new URLResource(url);
			mediaPlayer.media = audioElement;    
		}
		
		private var mediaPlayer:MediaPlayer;
		
		private function onTimeUpdated(event:TimeEvent):void
		{
			trace('time: ' + mediaPlayer.currentTime + ' duration: ' + mediaPlayer.duration);
		}
	}
}