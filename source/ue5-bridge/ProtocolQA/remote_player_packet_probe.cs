using MMOEngine;
using System.Text.Json;
int checks=0;var failures=new List<string>();
void Check(bool value,string label){checks++;if(!value)failures.Add(label);}
byte[] Packet(float x=343000,float y=467000,float z=5200,float speed=240,float vertical=-85,int session=71,int oid=31,int zone=207,int state=64,int heading=2048,int action=140,int hp=228,int mana=99,int endurance=100){
 var w=new DaocClient.Writer();foreach(var f in new[]{x,y,z,speed,vertical})w.FloatLE(f);w.Short((ushort)session);w.Short((ushort)oid);w.Short((ushort)zone);w.Byte((byte)state);w.Byte(0);w.Short(3);w.Short((ushort)heading);w.Byte((byte)action);w.Byte(1);w.Byte(0);w.Byte((byte)hp);w.Byte((byte)mana);w.Byte((byte)endurance);w.Short(0);return w.ToArray();
}
var bytes=Packet();Check(bytes.Length==40,"original1.127payload40bytes");
Check(DaocClient.TryReadPlayerPosition1127(new(bytes),out var p),"production decoder accepts original packet");
Check(p.X==343000&&p.Y==467000&&p.Z==5200,"absolute float coordinates and little endian");
Check(p.Session==71&&p.ObjectId==31&&p.Zone==207,"network session and object identity remain distinct");
Check(p.Speed==240&&p.VerticalSpeed==-85,"signed float speeds preserved");
Check(p.State==64&&p.Seat==3&&p.Heading==2048&&p.Action==140,"state seat heading action remain separate");
Check(p.Health==100&&p.Combat&&p.Mana==99&&p.Endurance==100,"combat high bit is not a health percentage");
for(int n=0;n<40;n++)Check(!DaocClient.TryReadPlayerPosition1127(new(bytes[..n]),out _),"truncated payload rejected:"+n);
Check(!DaocClient.TryReadPlayerPosition1127(new(bytes.Concat(new byte[]{0}).ToArray()),out _),"wrong protocol length rejected");
foreach(var f in new[]{float.NaN,float.PositiveInfinity,float.NegativeInfinity}){
 Check(!DaocClient.TryReadPlayerPosition1127(new(Packet(x:f)),out _),"invalid x");Check(!DaocClient.TryReadPlayerPosition1127(new(Packet(speed:f)),out _),"invalid speed");Check(!DaocClient.TryReadPlayerPosition1127(new(Packet(vertical:f)),out _),"invalid vertical");
}
Check(!DaocClient.TryReadPlayerPosition1127(new(Packet(session:0)),out _),"missing session rejected");
Check(!DaocClient.TryReadPlayerPosition1127(new(Packet(oid:0)),out _),"missing OID rejected");
Check(!DaocClient.TryReadPlayerPosition1127(new(Packet(hp:255)),out _),"impossible health rejected");
Check(!DaocClient.TryReadPlayerPosition1127(new(Packet(mana:101)),out _),"impossible mana rejected");
Check(!DaocClient.TryReadPlayerPosition1127(new(Packet(endurance:101)),out _),"impossible endurance rejected");
Check(DaocClient.TryReadPlayerPosition1127(new(Packet(speed:-160,state:28,action:2)),out p)&&p.Speed==-160&&p.State==28&&p.Action==2,"backward speed and climbing/stealth flags preserved");
Check(DaocClient.TryReadPlayerPosition1127(new(Packet(state:24,heading:40000)),out p)&&p.Heading==40000,"mounted heading field remains steed OID");
Check(DaocClient.TryReadPlayerPosition1127(new(Packet(hp:0)),out p)&&p.Health==0&&!p.Combat,"authoritative zero-health retained");
Console.WriteLine(JsonSerializer.Serialize(new{passed=failures.Count==0,checks,failures}));return failures.Count==0?0:1;
