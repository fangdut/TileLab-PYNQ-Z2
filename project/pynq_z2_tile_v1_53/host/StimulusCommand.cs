using System;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

// Shared by the real WPF player and native parser tests. No execution or paths
// are accepted from the command file: only names in the fixed source catalog.
public sealed class StimulusCommand {
 public readonly string Source, RequestId;
 public readonly int Version;
 private StimulusCommand(string source,string id,int version){Source=source;RequestId=id;Version=version;}
 public static bool ValidSource(string value){
  if(value==null)return false;
  switch(value){case "video":case "fast":case "ultrafast":case "real_video":case "holdout_video":case "dark_video":case "calib_video":case "transport_noise":case "burst":return true;}
  Match m=Regex.Match(value,@"\A(station_|real_|calib_|holdout_)([0-9]+)\z");
  if(!m.Success)return false;
  string prefix=m.Groups[1].Value,suffix=m.Groups[2].Value;
  int digits=prefix=="station_"?1:3,limit=prefix=="station_"?7:prefix=="real_"?117:prefix=="holdout_"?24:230,n;
  return suffix.Length==digits && int.TryParse(suffix,out n) && n<limit;
 }
 public static StimulusCommand Parse(string text){
  if(text==null || new UTF8Encoding(false,true).GetByteCount(text)>128)return null;
  text=text.Trim();if(ValidSource(text))return new StimulusCommand(text,null,0);
  Match m=Regex.Match(text,@"\ATILE_CMD_V1 ([0-9a-f]{32}) ([a-z0-9_]+)\z");
  if(!m.Success || !ValidSource(m.Groups[2].Value))return null;
  return new StimulusCommand(m.Groups[2].Value,m.Groups[1].Value,1);
 }
 public static string ReadBounded(string path){
  byte[] bytes=new byte[129];int n=0,k;
  using(FileStream f=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete)){
   while(n<bytes.Length && (k=f.Read(bytes,n,bytes.Length-n))>0)n+=k;
  }
  if(n>128)throw new InvalidDataException("HDMI command exceeds 128 bytes");
  int begin=n>=3 && bytes[0]==0xef && bytes[1]==0xbb && bytes[2]==0xbf?3:0;
  return new UTF8Encoding(false,true).GetString(bytes,begin,n-begin).Trim();
 }
}
