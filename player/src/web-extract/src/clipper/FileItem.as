package clipper
{
	public class FileItem
	{
		public function FileItem(o:Object=null)
		{
			if(o) {
				if(o.hasOwnProperty("title")) title = String(o.title);
				if(o.hasOwnProperty("file")) file = String(o.file);
				if(o.hasOwnProperty("size")) size = uint(o.size);
			}
		}
		public var title:String;
		public var file:String;
		public var size:uint;
		
		public static const dayNames:Array = "Sunday,Monday,Tuesday,Wednesday,Thursday,Friday,Saturday".split(",");
		public static const monthNames:Array = "January,February,March,April,May,June,July,August,September,October,November,December".split(",");
		
		public function get displayTitle():String {
			try {
				var d:Date = toStartDate()
				var ds:String;
				ds = dayNames[d.day]+", "+monthNames[d.month]+" "+FileList.pad(d.date,2);
			} catch(e:Error) {
				ds = e.toString();
			}
			return title+" >> "+ds;
		}
		public function toFileRequestDateKey():String {
			var bits:Array = file.split("-");
			bits.length = 3;
			return bits.join("-");
		}
		public function toStartDate():Date {
			// Filenames use format "YYYY-MM-DD-HH-mm-ss-hh.mp3"
			var raw:String = file.split(".").shift();
			// Time bits are given by splitting with "-"
			var bits:Array = raw.split("-");
			if(bits.length!=7) throw new Error("Invalid file name format found.");
			bits.reverse();
			var d:Date = new Date();
			d.fullYearUTC = bits.pop();
			d.monthUTC = bits.pop()-1;
			d.dateUTC = bits.pop();
			d.hoursUTC = bits.pop();
			d.minutesUTC = bits.pop();
			d.secondsUTC = bits.pop();
			d.millisecondsUTC = 10*bits.pop();
			return d;
		}
		public function toLocalDate():Date {
			// Filenames use format "YYYY-MM-DD-HH-mm-ss-hh.mp3"
			var raw:String = file.split(".").shift();
			// Time bits are given by splitting with "-"
			var bits:Array = raw.split("-");
			if(bits.length!=7) throw new Error("Invalid file name format found.");
			bits.reverse();
			var d:Date = new Date();
			d.fullYear = bits.pop();
			d.month = bits.pop()-1;
			d.date = bits.pop();
			d.hours = bits.pop();
			d.minutes = bits.pop();
			d.seconds = bits.pop();
			d.milliseconds = 10*bits.pop();
			return d;
		}
		public function toString():String {
			try {
				var d:Date = toStartDate()
				var ds:String = d.toDateString()+" "+d.toTimeString();
			} catch(e:Error) {
				ds = e.toString();
			}
			return "[FileItem:"+[title,file,size,ds]+"]";
		}
	}
}