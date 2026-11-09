using System.Reflection;
using System.Runtime.CompilerServices;
using System.Text.Json;
using MMOEngine;
var checks=0;var failures=new List<string>();
void Check(bool good,string label){checks++;if(!good)failures.Add(label);}
var client=(DaocClient)RuntimeHelpers.GetUninitializedObject(typeof(DaocClient));GC.SuppressFinalize(client);
var header=typeof(DaocClient).GetMethod("UseHeader",BindingFlags.Instance|BindingFlags.NonPublic)!;
foreach(var target in new[]{false,true})foreach(var ground in new[]{false,true}){
    client.BridgeGroundTargetSight(ground);var writer=new DaocClient.Writer();header.Invoke(client,new object[]{writer,1.25f,2.5f,3.75f,4.5f,8193,target});var bytes=writer.ToArray();
    int flags=(bytes[18]<<8)|bytes[19];int expected=(target?0xA000:0)|(ground?0x1000:0);
    Check(bytes.Length==20&&flags==expected,$"Independent target={target} ground={ground} flags");
    Check(BitConverter.ToSingle(bytes,0)==1.25f&&BitConverter.ToSingle(bytes,4)==2.5f&&BitConverter.ToSingle(bytes,8)==3.75f&&BitConverter.ToSingle(bytes,12)==4.5f&&bytes[16]==0&&bytes[17]==1,"Original movement header bytes preserved");
}
Console.WriteLine(JsonSerializer.Serialize(new{passed=failures.Count==0,checks,failures,normal_runtime_modified=false,server_started=false}));return failures.Count==0?0:1;
