using System;
using IoTDigitalTwin;
class PureLogicTests {
    static int assertions;
    static void Check(bool v,string m){assertions++;if(!v)throw new Exception(m);}
    static void Near(double a,double b,double e,string m){Check(Math.Abs(a-b)<e,m+": "+a+" vs "+b);}
    static void Main(){
        Near(DeviceMath.ClampFinite(-1,0,1),0,1e-8,"lower clamp");Near(DeviceMath.ClampFinite(10,0,1),1,1e-8,"upper clamp");bool rejected=false;try{DeviceMath.ClampFinite(float.NaN,0,1);}catch(ArgumentOutOfRangeException){rejected=true;}Check(rejected,"NaN rejected");
        for(int percent=0;percent<=100;percent++)Near(DeviceMath.BlindRailY(percent),DeviceMath.BlindClothBottomY(percent),1e-6,"rail/cloth synchronization "+percent);
        Near(DeviceMath.Move(10,15,1),11,1e-8,"opening step");Near(DeviceMath.Move(11,10,5),10,1e-8,"no overshoot");Near(DeviceMath.Move(15,15,1),15,1e-8,"stop");
        var random=new Random(83);
        foreach(var set in new[]{new[]{.257,.071,.016},new[]{-.030,-.790,.025}}){
            double top=set[0],bottom=set[1],radius=set[2],length=DeviceMath.CapsuleLength(top,bottom,radius);
            for(int i=0;i<1000;i++){double distance=random.NextDouble()*length,x,y;DeviceMath.CapsulePoint(distance,top,bottom,radius,out x,out y);double roundtrip=DeviceMath.CapsuleDistance(x,y,top,bottom,radius);double error=Math.Abs(distance-roundtrip);Near(Math.Min(error,length-error),0,1e-8,"capsule inverse");Check(y<=top+radius+1e-10&&y>=bottom-radius-1e-10,"chain within loop");double x2,y2;DeviceMath.CapsulePoint(distance+length,top,bottom,radius,out x2,out y2);Near(x2,x,1e-8,"loop wraps x");Near(y2,y,1e-8,"loop wraps y");}
            double[] joins={0,top-bottom,top-bottom+Math.PI*radius,2*(top-bottom)+Math.PI*radius,length};foreach(double join in joins){double x1,y1,x2,y2;DeviceMath.CapsulePoint(join-1e-7,top,bottom,radius,out x1,out y1);DeviceMath.CapsulePoint(join+1e-7,top,bottom,radius,out x2,out y2);Check(Math.Sqrt((x1-x2)*(x1-x2)+(y1-y2)*(y1-y2))<3e-7,"continuous loop joins");}
        }
        for(int digit=0;digit<=9;digit++){var d=DeviceMath.DotDigit(digit);Check(d.Length==5,"five rows");foreach(string row in d){Check(row.Length==3,"three columns");foreach(char c in row)Check(c=='0'||c=='1',"binary pixels");}}
        var u=new UnionFind(10);u.Join(0,1);u.Join(1,2);Check(u.Find(0)==u.Find(2),"transitive mesh islands");Check(u.Find(0)!=u.Find(3),"separate mesh islands");
        Console.WriteLine("PASS: "+assertions+" pure C# assertions (capsule motion, loop continuity, blind synchronization, clamping, digits, island connectivity).");
    }
}
