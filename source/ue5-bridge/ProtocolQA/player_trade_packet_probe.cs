using MMOEngine;
using System.Text.Json;
int checks=0;var failures=new List<string>();
void Check(bool value,string label){checks++;if(!value)failures.Add(label);}
byte[] Item(byte slot=40,byte flags=0,string name="Oak staff"){
 var w=new DaocClient.Writer();w.Byte(slot);w.Short(0);w.Byte(5);w.Byte(12);w.Byte(30);w.Byte(64);w.Byte(8);w.Byte(0);w.Short(25);w.Byte(100);w.Byte(99);w.Byte(98);w.Byte(3);w.Byte(1);w.Short(19);w.Byte(2);w.Short(31);w.Byte(flags);
 if((flags&8)!=0){w.Short(123);w.Pascal("First spell");}if((flags&16)!=0){w.Short(456);w.Pascal("Second spell");}
 w.Short(777);w.Pascal(name);return w.ToArray();
}
byte[] Window(byte[][]? items=null,byte[]? slots=null,string title="Trading with Codexfriend"){
 items??=new[]{Item()};slots??=new byte[]{40,41};var w=new DaocClient.Writer();
 for(int i=0;i<10;i++)w.Byte(i<slots.Length?slots[i]:(byte)0);
 w.Short(0);foreach(ushort x in new ushort[]{1,2,3,4,5})w.Short(x);w.Short(0);foreach(ushort x in new ushort[]{6,7,8,9,10})w.Short(x);w.Short(0);
 w.Byte((byte)items.Length);w.Byte(1);w.Byte(0);w.Byte(0);foreach(var item in items)foreach(byte x in item)w.Byte(x);w.Pascal(title);return w.ToArray();
}
bool Decode(byte[] data,out DaocClient.TradeWindow1127 value)=>DaocClient.TryReadTradeWindow1127(new(data),out value);
var packet=Window();Check(Decode(packet,out var trade),"modern original trade window decoded");
Check(!trade.Closed&&trade.PartnerPresent&&!trade.Repairing&&!trade.Combining,"original flags retained without invented acceptance");
Check(trade.OwnSlots.SequenceEqual(new byte[]{40,41,0,0,0,0,0,0,0,0}),"ten local slot identities retained");
Check(trade.OwnMoney.SequenceEqual(new[]{1,2,3,4,5})&&trade.PartnerMoney.SequenceEqual(new[]{6,7,8,9,10}),"mithril to copper denomination order and endian");
Check(trade.Title=="Trading with Codexfriend","original English title");
Check(trade.PartnerItemRecords.Length==1&&trade.PartnerItemRecords[0].SequenceEqual(Item()),"modern item record retained for existing ReadItem");
for(int n=0;n<packet.Length;n++)Check(!Decode(packet[..n],out _),"truncated offer rejected:"+n);
Check(!Decode(packet.Concat(new byte[]{0}).ToArray(),out _),"trailing data rejected");
Check(Decode(new byte[40],out var close)&&close.Closed&&close.OwnSlots.Length==0,"exact original close payload");
var corruptClose=new byte[40];corruptClose[39]=1;Check(!Decode(corruptClose,out _),"nonzero incomplete close rejected");
Check(Decode(Window(Array.Empty<byte[]>()),out var empty)&&!empty.Closed&&empty.PartnerItemRecords.Length==0,"open empty offer remains distinct from close");
foreach(byte flags in new byte[]{0,1,8,16,24,25}){
 var raw=Item(flags:flags,name:"Épée 2");Check(Decode(Window(new[]{raw}),out var x)&&x.PartnerItemRecords[0].SequenceEqual(raw),"optional spell/dye/emblem record boundary:"+flags);
}
var ten=Enumerable.Range(40,10).Select(x=>Item((byte)x)).ToArray();Check(Decode(Window(ten),out var full)&&full.PartnerItemRecords.Length==10,"ten partner offers accepted");
Check(!Decode(Window(ten.Append(Item(60)).ToArray()),out _),"over ten offers rejected");
Check(!Decode(Window(new[]{Item(),Item()}),out _),"duplicate partner slot rejected");
Check(!Decode(Window(slots:new byte[]{40,40}),out _),"duplicate own slot rejected");
foreach(int at in new[]{10,22,34}){var bad=(byte[])packet.Clone();bad[at]=1;Check(!Decode(bad,out _),"reserved field rejected:"+at);}
foreach(int at in new[]{37,38,39}){var bad=(byte[])packet.Clone();bad[at]=2;Check(!Decode(bad,out _),"invalid boolean rejected:"+at);}
var absent=(byte[])packet.Clone();absent[37]=0;Check(!Decode(absent,out _),"items cannot name an absent partner");
var maxCoins=(byte[])packet.Clone();maxCoins[12]=255;maxCoins[13]=255;Check(Decode(maxCoins,out var rich)&&rich.OwnMoney[0]==65535,"unsigned coin maximum retained");
Check(DaocClient.TryBuildPlayerTradeRequest(1,new[]{40,41},new[]{1,2,3,4,5},out var offer)&&offer.SequenceEqual(new byte[]{1,0,0,0,40,41,0,0,0,0,0,0,0,0,0,0,0,1,0,2,0,3,0,4,0,5}),"original update payload exact golden bytes");
Check(DaocClient.TryBuildPlayerTradeRequest(0,Array.Empty<int>(),Array.Empty<int>(),out var cancel)&&cancel.SequenceEqual(new byte[]{0,0,0,0}),"original cancel payload exact bytes");
Check(DaocClient.TryBuildPlayerTradeRequest(2,Array.Empty<int>(),Array.Empty<int>(),out var accept)&&accept.SequenceEqual(new byte[]{2,0,0,0}),"original accept payload exact bytes");
foreach(int action in new[]{-1,3,255})Check(!DaocClient.TryBuildPlayerTradeRequest(action,Array.Empty<int>(),Array.Empty<int>(),out _),"unsupported trade action rejected");
foreach(int slot in new[]{-1,1,21,39,80,65535})Check(!DaocClient.TryBuildPlayerTradeRequest(1,new[]{slot},new int[5],out _),"non-backpack outgoing slot rejected:"+slot);
Check(!DaocClient.TryBuildPlayerTradeRequest(1,new[]{40,40},new int[5],out _),"duplicate outgoing ownership slot rejected");
Check(!DaocClient.TryBuildPlayerTradeRequest(1,Enumerable.Range(40,11).ToArray(),new int[5],out _),"outgoing offer limit");
foreach(int amount in new[]{-1,65536,int.MaxValue})Check(!DaocClient.TryBuildPlayerTradeRequest(1,new[]{40},new[]{0,0,0,0,amount},out _),"invalid outgoing money rejected");
Check(!DaocClient.TryBuildPlayerTradeRequest(1,new[]{40},new int[4],out _),"all five denominations required");
Check(!DaocClient.TryBuildPlayerTradeRequest(2,new[]{40},new int[5],out _),"accept cannot silently change the offer");
Console.WriteLine(JsonSerializer.Serialize(new{passed=failures.Count==0,checks,failures}));return failures.Count==0?0:1;
