using UnityEngine;
namespace IoTDigitalTwin {
    public sealed class DynamicDotDisplay:MonoBehaviour {
        public MeshFilter filter;public int verticesPerDot=8;
        Mesh owned;Color[] colors;
        void Awake(){owned=Instantiate(filter.sharedMesh);owned.name="Live_LED_Dots";filter.sharedMesh=owned;colors=new Color[owned.vertexCount];}
        public void SetValue(int value){
            if(owned==null)return;value=Mathf.Clamp(value,0,99);int[] digits={value/10,value%10};
            for(int digit=0;digit<2;digit++){
                string[] pattern=DeviceMath.DotDigit(digits[digit]);
                for(int row=0;row<5;row++)for(int col=0;col<3;col++)SetDot(digit*15+row*3+col,pattern[row][col]=='1');
            }
            int level=Mathf.RoundToInt(value/99f*4);for(int i=0;i<5;i++)SetDot(30+i,i<=level);SetDot(35,true);
            owned.colors=colors;
        }
        void SetDot(int dot,bool on){Color color=on?new Color(.88f,.84f,1,1):new Color(.1f,.11f,.1f,.10f);for(int i=0;i<verticesPerDot;i++)colors[dot*verticesPerDot+i]=color;}
        void OnDestroy(){if(owned)Destroy(owned);}
    }
}
