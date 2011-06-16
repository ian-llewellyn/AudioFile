package clipper
{
	public class ServiceItem
	{
		public function ServiceItem(o:Object=null)
		{
			if(o) {
				if(o.hasOwnProperty("title")) title = String(o.title);
				if(o.hasOwnProperty("id")) id = String(o.id);
			}
			index = new Object();
		}
		private var index:Object;
		
		public var title:String;
		public var id:String;
		
		public static function dateKey(d:Date):String {
			return [FileList.pad(d.fullYear,4),FileList.pad(d.month+1,2),FileList.pad(d.date,2)].join("-");
		}
		public function indexDate(d:Date,files:Array):void {
			index[dateKey(d)] = files;
		}
		public function filesFor(d:Date):Array {
			var a:Array = index[dateKey(d)];
			return a ? a : new Array();
		}
		public function toString():String {
			return "[ServiceItem:"+[title,id]+"]";
		}
	}
}