using System;
namespace IoTDigitalTwin {
    // Pure logic is deliberately independent of Unity so it can be exercised offline.
    public static class DeviceMath {
        public static float ClampFinite(float value, float min, float max) {
            if(float.IsNaN(value)||float.IsInfinity(value)) throw new ArgumentOutOfRangeException("value","Value must be finite.");
            return Math.Max(min,Math.Min(max,value));
        }
        public static float Move(float current,float target,float distance) {
            if(distance<0)throw new ArgumentOutOfRangeException("distance");
            return Math.Abs(target-current)<=distance ? target : current+Math.Sign(target-current)*distance;
        }
        public static double Wrap(double value,double period) { return (value%period+period)%period; }
        public static double CapsuleLength(double top,double bottom,double radius) {return 2*(top-bottom)+2*Math.PI*radius;}
        public static void CapsulePoint(double distance,double top,double bottom,double radius,out double horizontal,out double vertical) {
            double straight=top-bottom;distance=Wrap(distance,CapsuleLength(top,bottom,radius));
            if(distance<straight){horizontal=radius;vertical=top-distance;}
            else if(distance<straight+Math.PI*radius){double a=(distance-straight)/radius;horizontal=radius*Math.Cos(a);vertical=bottom-radius*Math.Sin(a);}
            else if(distance<2*straight+Math.PI*radius){horizontal=-radius;vertical=bottom+distance-straight-Math.PI*radius;}
            else{double a=(distance-2*straight-Math.PI*radius)/radius;horizontal=-radius*Math.Cos(a);vertical=top+radius*Math.Sin(a);}
        }
        public static double CapsuleDistance(double horizontal,double vertical,double top,double bottom,double radius) {
            double straight=top-bottom;
            if(vertical>=bottom && vertical<=top)return horizontal>=0?top-vertical:straight+Math.PI*radius+vertical-bottom;
            if(vertical<bottom)return straight+radius*Math.Atan2(bottom-vertical,horizontal);
            return 2*straight+Math.PI*radius+radius*Math.Atan2(vertical-top,-horizontal);
        }
        public static float BlindRailY(float percent) {return -.484f+.42525f*ClampFinite(percent,0,100)/100;}
        public static float BlindClothBottomY(float percent) {return -.034f-.45f*(1-.945f*ClampFinite(percent,0,100)/100);}
        public static string[] DotDigit(int digit) {
            string[][] digits={new[]{"111","101","101","101","111"},new[]{"010","110","010","010","111"},new[]{"111","001","111","100","111"},new[]{"111","001","111","001","111"},new[]{"101","101","111","001","001"},new[]{"111","100","111","001","111"},new[]{"111","100","111","101","111"},new[]{"111","001","001","001","001"},new[]{"111","101","111","101","111"},new[]{"111","101","111","001","001"}};
            if(digit<0||digit>9)throw new ArgumentOutOfRangeException("digit");return digits[digit];
        }
    }
    public sealed class UnionFind {
        readonly int[] parent,rank;
        public UnionFind(int count){parent=new int[count];rank=new int[count];for(int i=0;i<count;i++)parent[i]=i;}
        public int Find(int i){while(parent[i]!=i){parent[i]=parent[parent[i]];i=parent[i];}return i;}
        public void Join(int a,int b){a=Find(a);b=Find(b);if(a==b)return;if(rank[a]<rank[b])parent[a]=b;else{parent[b]=a;if(rank[a]==rank[b])rank[a]++;}}
    }
}
