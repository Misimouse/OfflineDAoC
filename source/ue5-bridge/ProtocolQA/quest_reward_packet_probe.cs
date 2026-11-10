using MMOEngine;
using System.Text.Json;
int checks=0;var failures=new List<string>();
void Check(bool ok,string label){checks++;if(!ok)failures.Add(label);}
byte[] Item(byte flags=0,string name="Oak staff") {
 var w=new DaocClient.Writer();w.Short(0);w.Byte(5);w.Byte(12);w.Byte(30);w.Byte(64);w.Byte(8);w.Byte(0);w.Short(25);w.Byte(100);w.Byte(99);w.Byte(98);w.Byte(3);w.Byte(1);w.Short(19);w.Byte(2);w.Short(31);w.Byte(flags);
 if((flags&8)!=0){w.Short(123);w.Pascal("First spell");}if((flags&16)!=0){w.Short(456);w.Pascal("Second spell");}w.Short(777);w.Pascal(name);return w.ToArray();
}
byte[] Window(bool offer=false,int required=1,byte[][]? fixedItems=null,byte[][]? options=null,string story="Original story",string title="Quest of Éire"){
 fixedItems??=new[]{Item()};options??=new[]{Item(8,"Choice A"),Item(16,"Choice B")};var w=new DaocClient.Writer();
 w.Short((ushort)(offer?0x22:0x21));w.Short(1234);w.Short(4321);w.Short(7);w.Short(8);w.Byte((byte)(offer?2:1));w.Byte(1);w.Pascal(title);w.Pascal("Original summary");w.Short((ushort)story.Length);w.Fixed(story,story.Length);w.Short(1234);w.Byte(2);w.Pascal("First goal\r");w.Pascal("Second goal\r");w.Int(4000000000);w.Byte(250);w.Byte((byte)fixedItems.Length);foreach(var i in fixedItems)w.Bytes(i);w.Byte((byte)required);w.Byte((byte)options.Length);foreach(var i in options)w.Bytes(i);return w.ToArray();
}
bool Decode(byte[] raw,out DaocClient.QuestRewardDialog1127 value)=>DaocClient.TryReadQuestRewardDialog1127(new(raw),out value);
var raw=Window();Check(Decode(raw,out var d),"complete original reward dialog");
Check(d.Code==0x21&&d.QuestId==1234&&d.GiverId==4321&&d.Data3==7&&d.Data4==8,"original identities and opaque data retained");
Check(d.Name=="Quest of Éire"&&d.Summary=="Original summary"&&d.Story=="Original story","original Windows1252 text");
Check(d.Goals.SequenceEqual(new[]{"First goal\r","Second goal\r"}),"goals retain original text and order");
Check(d.Money==4000000000&&d.ExperiencePercent==250,"unsigned money and original XP byte not clamped");
Check(d.FixedItemRecords.Single().AsSpan(1).SequenceEqual(Item())&&d.OptionalItemRecords.Length==2&&d.RequiredChoices==1,"slotless modern reward item boundaries");
Check(d.FixedItemRecords.All(i=>i[0]==0)&&d.OptionalItemRecords.All(i=>i[0]==0),"neutral presentation slot added only after decoding");
Check(d.OptionalItemRecords[0].AsSpan(1).SequenceEqual(Item(8,"Choice A")),"slotless first spell record boundary");
Check(d.OptionalItemRecords[1].AsSpan(1).SequenceEqual(Item(16,"Choice B")),"slotless second spell record boundary");
for(int n=0;n<raw.Length;n++)Check(!Decode(raw[..n],out _),"truncated packet:"+n);
Check(!Decode(raw.Concat(new byte[]{0}).ToArray(),out _),"trailing bytes refused");
foreach(int at in new[]{0,1,10,11}){var bad=(byte[])raw.Clone();bad[at]=at==10?(byte)2:at==11?(byte)2:(byte)255;Check(!Decode(bad,out _),"invalid header:"+at);}
foreach(int at in new[]{2,4}){var bad=(byte[])raw.Clone();bad[at]=bad[at+1]=0;Check(!Decode(bad,out _),"zero original identity:"+at);}
var mismatch=(byte[])raw.Clone();int repeat=12+1+"Quest of Éire".Length+1+"Original summary".Length+2+"Original story".Length;mismatch[repeat]=0;Check(!Decode(mismatch,out _),"repeated quest ID mismatch");
Check(!Decode(Window(required:3),out _),"required choices exceed options");
Check(!Decode(Window(required:9,options:Enumerable.Range(0,9).Select(_=>Item()).ToArray()),out _),"request cannot encode over eight choices");
Check(Decode(Window(offer:true),out var offer)&&offer.Code==0x22&&offer.DialogType==2,"original offer distinct from reward");
Check(!DaocClient.TryBuildQuestRewardChoice(offer,new[]{0},out _),"offer cannot finish as reward");
Check(DaocClient.TryBuildQuestOfferResponse(offer,true,out var yes)&&yes.SequenceEqual(new byte[]{4,210,16,225,0,0,100,1,0,0}),"original offer acceptance uses QuestSubscribe identity and code");
Check(DaocClient.TryBuildQuestOfferResponse(offer,false,out var no)&&no.SequenceEqual(new byte[]{4,210,16,225,0,0,100,0,0,0}),"original offer decline");
Check(!DaocClient.TryBuildQuestOfferResponse(d,true,out _),"reward cannot be accepted as a fresh offer");
Check(!DaocClient.TryBuildQuestOfferResponse(null!,true,out _),"null offer cannot be accepted");
Check(Decode(Window(required:0,fixedItems:Array.Empty<byte[]>(),options:Array.Empty<byte[]>(),story:""),out var empty)&&empty.Goals.Length==2,"empty rewards and story supported");
Check(DaocClient.TryBuildQuestRewardChoice(empty,null!,out var noChoice)&&noChoice.Length==20&&noChoice[1]==0,"zero-choice original finish request");
Check(DaocClient.TryBuildQuestRewardChoice(d,new[]{1},out var request)&&request.Length==20,"original request length");
Check(request.SequenceEqual(new byte[]{1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,4,210,16,225}),"original request field order and big endian identities");
Check(DaocClient.QuestRewardWireCode==0x40,"literal original handler code; no second XOR or world initialization");
foreach(var choice in new[]{Array.Empty<int>(),new[]{0,1},new[]{-1},new[]{2},new[]{256}})Check(!DaocClient.TryBuildQuestRewardChoice(d,choice,out _),"invalid selection:"+string.Join(',',choice));
Check(Decode(Window(required:2),out var two)&&!DaocClient.TryBuildQuestRewardChoice(two,new[]{0,0},out _),"duplicate reward index refused");
foreach(byte flags in new byte[]{0,8,16,24,25})Check(Decode(Window(fixedItems:new[]{Item(flags)},options:new[]{Item(flags)}),out _),"modern optional item fields:"+flags);
Check(Decode(Window(required:8,options:Enumerable.Range(0,8).Select(_=>Item()).ToArray()),out var eight)&&DaocClient.TryBuildQuestRewardChoice(eight,Enumerable.Range(0,8).ToArray(),out _),"eight original choices supported");
Check(!DaocClient.TryReadQuestRewardDialog1127(null!,out _),"null reader refused");
Check(!DaocClient.TryBuildQuestRewardChoice(null!,Array.Empty<int>(),out _),"null dialog refused");
Console.WriteLine(JsonSerializer.Serialize(new{passed=failures.Count==0,checks,failures}));return failures.Count==0?0:1;
