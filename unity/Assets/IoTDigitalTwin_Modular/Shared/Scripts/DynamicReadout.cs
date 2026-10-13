using System;
using System.Collections.Generic;
using UnityEngine;
namespace IoTDigitalTwin {
    [Serializable] public class FontGlyph {public int code;public float u0,v0,u1,v1,width,height,advance,bottom;}
    [Serializable] public class RuntimeFontAtlas {public string texture;public float digitHeight,capitalHeight;public FontGlyph[] glyphs;}
    [RequireComponent(typeof(MeshFilter),typeof(MeshRenderer))]
    public sealed class DynamicReadout:MonoBehaviour {
        public FontGlyph[] glyphs;public float height=.01f,referencePixels=64;public Color tint=Color.white;
        public string initialText;
        Mesh owned;Dictionary<int,FontGlyph> lookup;string last;
        public string Value{get{return last??initialText;}}public Mesh PreviewMesh{get{return owned;}}
        void Awake(){Initialize();SetText(initialText);}
        void Initialize(){if(owned)return;owned=new Mesh();owned.name=name+"_LiveText";owned.MarkDynamic();GetComponent<MeshFilter>().sharedMesh=owned;lookup=new Dictionary<int,FontGlyph>();foreach(var g in glyphs)lookup[g.code]=g;last=null;}
        public void SetText(string text){
            text=text??"";Initialize();if(last==text)return;last=text;initialText=text;var vertices=new List<Vector3>();var uv=new List<Vector2>();var colors=new List<Color>();var triangles=new List<int>();float width=0;FontGlyph g;
            foreach(char c in text)if(lookup.TryGetValue(c,out g))width+=g.advance;
            float x=-width/2,scale=height/referencePixels;
            foreach(char c in text){if(!lookup.TryGetValue(c,out g))continue;int k=vertices.Count;vertices.Add(new Vector3(x*scale,g.bottom*scale,0));vertices.Add(new Vector3((x+g.width)*scale,g.bottom*scale,0));vertices.Add(new Vector3((x+g.width)*scale,(g.bottom+g.height)*scale,0));vertices.Add(new Vector3(x*scale,(g.bottom+g.height)*scale,0));uv.Add(new Vector2(g.u0,g.v0));uv.Add(new Vector2(g.u1,g.v0));uv.Add(new Vector2(g.u1,g.v1));uv.Add(new Vector2(g.u0,g.v1));for(int i=0;i<4;i++)colors.Add(tint);triangles.AddRange(new[]{k,k+1,k+2,k,k+2,k+3});x+=g.advance;}
            // Centre the visible line vertically; dimensions are explicitly in metres.
            if(vertices.Count>0){float lo=vertices[0].y,hi=lo;foreach(var v in vertices){lo=Mathf.Min(lo,v.y);hi=Mathf.Max(hi,v.y);}for(int i=0;i<vertices.Count;i++)vertices[i]-=Vector3.up*((lo+hi)/2);}
            owned.Clear();owned.SetVertices(vertices);owned.SetUVs(0,uv);owned.SetColors(colors);owned.SetTriangles(triangles,0);owned.RecalculateBounds();
        }
        public void SetColor(Color color){tint=color;string text=Value;last=null;SetText(text);}
        // Editor-created preview meshes are persisted as assets; runtime ownership starts at Awake.
        public void ReleaseEditorOwnership(){owned=null;lookup=null;last=null;}
        void OnDestroy(){if(owned)Destroy(owned);}
    }
}
