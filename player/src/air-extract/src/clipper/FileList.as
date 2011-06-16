package clipper
{
	import com.adobe.serialization.json.JSONDecoder;
	
	import flash.events.ErrorEvent;
	import flash.events.Event;
	import flash.events.EventDispatcher;
	import flash.events.IEventDispatcher;
	import flash.events.IOErrorEvent;
	import flash.events.SecurityErrorEvent;
	import flash.net.URLLoader;
	import flash.net.URLRequest;
	import flash.net.URLRequestMethod;
	import flash.net.URLVariables;
	
	import mx.collections.ArrayCollection;
	import mx.collections.IList;
	
	[Event(name="complete",type="flash.events.Event")]
	[Event(name="ioError",type="flash.events.IOErrorEvent")]
	[Event(name="securityError",type="flash.events.SecurityErrorEvent")]
	[Event(name="error",type="flash.events.ErrorEvent")]
	public class FileList extends EventDispatcher
	{
		/**
		 * fileListUrl:String = the url of the service to return files in JSON format
		 */
		public function FileList(fileListUrl:String)
		{
			super();
			_fileListUrl = fileListUrl;
		}
		/**
		 * fileListUrl:String = the url of the service to return files in JSON format
		 */
		private var _fileListUrl:String;
		/**
		 * Given a ServiceItem and a Date, request current filelist and dispatch a complete event
		 * on receipt.
		 */
		public function loadFor(service:ServiceItem=null,date:Date=null):void {
			// Clean up to make sure data is clean by take down old and build new
			_results = null;
			unbuildLoader();
			buildLoader();
			// Set flag
			_loadComplete = false;
			// Process the load
			var uv:URLVariables = new URLVariables();
			if(service) {
				uv.service = service.id;
				uv.date = dateString(date);
				_service = service;
				_date = date;
			} else {
				_service = null;
				_date = null;
			}
			var ur:URLRequest = new URLRequest(_fileListUrl);
			ur.method = URLRequestMethod.GET; 
			ur.data = uv;
			loader.load(ur);
		}
		/**
		 * Returns service for last load.
		 */
		public function get service():ServiceItem {
			return _service;
		}
		private var _service:ServiceItem;
		/**
		 * Returns date for last load.
		 */
		public function get date():Date {
			return _date;
		}
		private var _date:Date;
		/**
		 * Returns the results of the last load as an IList for use in display
		 */
		public function get resultList():IList {
			if(!results) return null;
			return new ArrayCollection(results);
		}
		/**
		 * Returns an array of results
		 */
		public function get results():Array {
			return _results;
		}
		private var _results:Array;
		
		public function get loadComplete():Boolean {
			return _loadComplete;
		}
		private var _loadComplete:Boolean = false;
		
		private var loader:URLLoader;
		protected function buildLoader():void {
			unbuildLoader();
			loader = new URLLoader();
			loader.addEventListener(SecurityErrorEvent.SECURITY_ERROR,dispatchEvent);
			loader.addEventListener(IOErrorEvent.IO_ERROR,dispatchEvent);
			loader.addEventListener(Event.COMPLETE,processFilelist);
		}
		protected function unbuildLoader():void {
			if(!loader) return;
			loader.removeEventListener(SecurityErrorEvent.SECURITY_ERROR,dispatchEvent);
			loader.removeEventListener(IOErrorEvent.IO_ERROR,dispatchEvent);
			loader.removeEventListener(Event.COMPLETE,processFilelist);
			loader = null;
		}
		protected function processFilelist(event:Event):void {
			var j:JSONDecoder = new JSONDecoder(loader.data);
			var a:Array = j.getValue().files;
			if(a) {
				for(var i:int=0;i<a.length;i++) {
					var fi:FileItem = new FileItem(a[i]);
					a[i] = fi;
				}
			}
			_results = a;
			// Set flag and dispatch event
			_loadComplete = true;
			dispatchEvent(new Event(Event.COMPLETE));
		}
		////////////////////////
		// Static utilities
		////////////////////////
		/**
		 * Utility shortcut to format date in to YYYY-MM-DD, if date is null, use a new Date(); (eg: default to today)
		 */
		public static function dateString(date:Date):String {
			if(!date) date = new Date();
			var y:String = pad(date.fullYear,4);
			// Flash dates are zero indexed
			var m:String = pad(1+date.month,2);
			var d:String = pad(date.date,2);
			return [y,m,d].join("-");
		}
		/**
		 * Utility to pad an int with zeros
		 */
		public static function pad(n:int,num:uint):String {
			var s:String = n.toString();
			while(s.length<num) s = "0"+s;
			return s;
		}
	}
}