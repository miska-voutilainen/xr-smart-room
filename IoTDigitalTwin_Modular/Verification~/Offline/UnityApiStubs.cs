// Offline compile/test doubles. NOT Unity Engine. Never copy this file into Assets.
using System;using System.Collections;using System.Collections.Generic;using System.Linq;
namespace UnityEngine {
 public class Object {public string name;public static implicit operator bool(Object o){return o!=null;}public static bool operator !(Object o){return o==null;}public static T Instantiate<T>(T o)where T:Object {if(o is Mesh)return (T)(Object)((Mesh)(Object)o).Clone();return o;}public static void Destroy(Object o){}public static void DestroyImmediate(Object o){}public static T FindObjectOfType<T>()where T:Object{return null;}}
 public class Component:Object {internal GameObject owner;public GameObject gameObject {get {if(owner==null)owner=new GameObject();return owner;}}public Transform transform{get{return gameObject.transform;}}public string tag{get{return gameObject.tag;}set{gameObject.tag=value;}}public T GetComponent<T>()where T:Component{return gameObject.GetComponent<T>();}public T[] GetComponentsInChildren<T>(bool inactive=false)where T:Component{return gameObject.GetComponentsInChildren<T>(inactive);}}
 public class Behaviour:Component {public bool enabled=true;}
 public class MonoBehaviour:Behaviour {public Coroutine StartCoroutine(IEnumerator i){return new Coroutine();}}
 public class Coroutine{}
 public class GameObject:Object {
  readonly List<Component> components=new List<Component>();public Transform transform;public string tag;
  public GameObject(string n="Object"){name=n;transform=new Transform();transform.owner=this;components.Add(transform);}
  public T AddComponent<T>()where T:Component{var c=(T)Activator.CreateInstance(typeof(T));c.owner=this;components.Add(c);return c;}
  public T GetComponent<T>()where T:Component{return components.OfType<T>().FirstOrDefault();}
  public T[] GetComponentsInChildren<T>(bool inactive=false)where T:Component{var l=new List<T>();l.AddRange(components.OfType<T>());foreach(var c in transform.children)l.AddRange(c.gameObject.GetComponentsInChildren<T>(inactive));return l.ToArray();}
  public static GameObject CreatePrimitive(PrimitiveType p){var g=new GameObject();g.AddComponent<MeshFilter>();g.AddComponent<MeshRenderer>();g.AddComponent<BoxCollider>();return g;}
 }
 public class Transform:Component {
  public Vector3 localPosition,localScale=Vector3.one;public Quaternion localRotation=Quaternion.identity;public List<Transform> children=new List<Transform>();Transform p;
  public Transform parent{get{return p;}set{if(p!=null)p.children.Remove(this);p=value;if(p!=null)p.children.Add(this);}}
  public void SetParent(Transform t,bool keep=true){var pos=position;var rot=rotation;parent=t;if(keep){position=pos;rotation=rot;}}
  public Matrix4x4 localToWorldMatrix{get{return parent==null?Matrix4x4.TRS(localPosition,localRotation,localScale):parent.localToWorldMatrix*Matrix4x4.TRS(localPosition,localRotation,localScale);}}
  public Vector3 position{get{return localToWorldMatrix.MultiplyPoint(Vector3.zero);}set{localPosition=parent==null?value:parent.InverseTransformPoint(value);}}
  public Quaternion rotation{get{return parent==null?localRotation:parent.rotation*localRotation;}set{localRotation=parent==null?value:Quaternion.Inverse(parent.rotation)*value;}}
  public Vector3 forward{get{return rotation*Vector3.forward;}}public Vector3 up{get{return rotation*Vector3.up;}}public Vector3 right{get{return rotation*Vector3.right;}}
  public Vector3 TransformPoint(Vector3 v){return localToWorldMatrix.MultiplyPoint(v);}public Vector3 InverseTransformPoint(Vector3 v){return localToWorldMatrix.inverse.MultiplyPoint(v);}public Vector3 InverseTransformVector(Vector3 v){return localToWorldMatrix.inverse.MultiplyVector(v);}public Vector3 InverseTransformDirection(Vector3 v){return Quaternion.Inverse(rotation)*v;}
 }
 public struct Vector2 {public float x,y;public Vector2(float a,float b){x=a;y=b;}public static Vector2 zero{get{return new Vector2();}}public float magnitude{get{return (float)Math.Sqrt(x*x+y*y);}}public static Vector2 operator-(Vector2 a,Vector2 b){return new Vector2(a.x-b.x,a.y-b.y);}public static implicit operator Vector2(Vector3 a){return new Vector2(a.x,a.y);}public static implicit operator Vector3(Vector2 a){return new Vector3(a.x,a.y,0);}}
 public struct Vector3 {
  public float x,y,z;public Vector3(float a,float b,float c){x=a;y=b;z=c;}
  public float magnitude{get{return (float)Math.Sqrt(sqrMagnitude);}}public float sqrMagnitude{get{return x*x+y*y+z*z;}}public Vector3 normalized{get{return magnitude>0?this/magnitude:zero;}}
  public static Vector3 zero{get{return new Vector3();}}public static Vector3 one{get{return new Vector3(1,1,1);}}public static Vector3 up{get{return new Vector3(0,1,0);}}public static Vector3 right{get{return new Vector3(1,0,0);}}public static Vector3 forward{get{return new Vector3(0,0,1);}}public static Vector3 back{get{return new Vector3(0,0,-1);}}
  public static Vector3 operator+(Vector3 a,Vector3 b){return new Vector3(a.x+b.x,a.y+b.y,a.z+b.z);}public static Vector3 operator-(Vector3 a,Vector3 b){return a+-b;}public static Vector3 operator-(Vector3 a){return a*-1;}public static Vector3 operator*(Vector3 a,float b){return new Vector3(a.x*b,a.y*b,a.z*b);}public static Vector3 operator*(float b,Vector3 a){return a*b;}public static Vector3 operator/(Vector3 a,float b){return a*(1/b);}
  public static float Dot(Vector3 a,Vector3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}public static Vector3 Cross(Vector3 a,Vector3 b){return new Vector3(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x);}public static Vector3 Project(Vector3 a,Vector3 b){return b*(Dot(a,b)/b.sqrMagnitude);}public static Vector3 Lerp(Vector3 a,Vector3 b,float t){return a+(b-a)*Mathf.Clamp01(t);}public override string ToString(){return x+","+y+","+z;}
 }
 public struct Vector4 {public float x,y,z,w;public Vector4(float a,float b,float c,float d){x=a;y=b;z=c;w=d;}public static implicit operator Vector3(Vector4 v){return new Vector3(v.x,v.y,v.z);}}
 public struct Quaternion {
  internal System.Numerics.Quaternion q;public static Quaternion identity{get{return new Quaternion{q=System.Numerics.Quaternion.Identity};}}
  public static Quaternion Inverse(Quaternion a){return new Quaternion{q=System.Numerics.Quaternion.Inverse(a.q)};}public static Quaternion operator*(Quaternion a,Quaternion b){return new Quaternion{q=a.q*b.q};}public static Vector3 operator*(Quaternion a,Vector3 v){var r=System.Numerics.Vector3.Transform(new System.Numerics.Vector3(v.x,v.y,v.z),a.q);return new Vector3(r.X,r.Y,r.Z);}
  public static Quaternion AngleAxis(float angle,Vector3 axis){return new Quaternion{q=System.Numerics.Quaternion.CreateFromAxisAngle(new System.Numerics.Vector3(axis.x,axis.y,axis.z),angle*Mathf.PI/180)};}public static Quaternion Euler(float x,float y,float z){return AngleAxis(y,Vector3.up)*AngleAxis(x,Vector3.right)*AngleAxis(z,Vector3.forward);}public static Quaternion Slerp(Quaternion a,Quaternion b,float t){return new Quaternion{q=System.Numerics.Quaternion.Slerp(a.q,b.q,Mathf.Clamp01(t))};}
  public static Quaternion LookRotation(Vector3 f,Vector3 up){f=f.normalized;Vector3 x=Vector3.Cross(up,f).normalized,y=Vector3.Cross(f,x);var m=new System.Numerics.Matrix4x4(x.x,x.y,x.z,0,y.x,y.y,y.z,0,f.x,f.y,f.z,0,0,0,0,1);return new Quaternion{q=System.Numerics.Quaternion.CreateFromRotationMatrix(m)};}
 }
 public struct Matrix4x4 {
  float[,] a;public static Matrix4x4 identity{get{var m=new Matrix4x4{a=new float[4,4]};for(int i=0;i<4;i++)m.a[i,i]=1;return m;}}
  public void SetColumn(int c,Vector4 v){a[0,c]=v.x;a[1,c]=v.y;a[2,c]=v.z;a[3,c]=v.w;}public Vector4 GetColumn(int c){return new Vector4(a[0,c],a[1,c],a[2,c],a[3,c]);}
  System.Numerics.Matrix4x4 N{get{return new System.Numerics.Matrix4x4(a[0,0],a[0,1],a[0,2],a[0,3],a[1,0],a[1,1],a[1,2],a[1,3],a[2,0],a[2,1],a[2,2],a[2,3],a[3,0],a[3,1],a[3,2],a[3,3]);}}
  public float determinant{get{return N.GetDeterminant();}}public Matrix4x4 inverse{get{System.Numerics.Matrix4x4 n;System.Numerics.Matrix4x4.Invert(N,out n);var m=identity;float[,] v={{n.M11,n.M12,n.M13,n.M14},{n.M21,n.M22,n.M23,n.M24},{n.M31,n.M32,n.M33,n.M34},{n.M41,n.M42,n.M43,n.M44}};m.a=v;return m;}}
  public Vector3 MultiplyVector(Vector3 v){return new Vector3(a[0,0]*v.x+a[0,1]*v.y+a[0,2]*v.z,a[1,0]*v.x+a[1,1]*v.y+a[1,2]*v.z,a[2,0]*v.x+a[2,1]*v.y+a[2,2]*v.z);}public Vector3 MultiplyPoint(Vector3 v){return MultiplyVector(v)+(Vector3)GetColumn(3);}
  public static Matrix4x4 operator*(Matrix4x4 x,Matrix4x4 y){var m=identity;for(int i=0;i<4;i++)for(int j=0;j<4;j++){m.a[i,j]=0;for(int k=0;k<4;k++)m.a[i,j]+=x.a[i,k]*y.a[k,j];}return m;}
  public static Matrix4x4 TRS(Vector3 t,Quaternion r,Vector3 s){var m=identity;var x=r*Vector3.right*s.x;var y=r*Vector3.up*s.y;var z=r*Vector3.forward*s.z;m.SetColumn(0,new Vector4(x.x,x.y,x.z,0));m.SetColumn(1,new Vector4(y.x,y.y,y.z,0));m.SetColumn(2,new Vector4(z.x,z.y,z.z,0));m.SetColumn(3,new Vector4(t.x,t.y,t.z,1));return m;}
 }
 public struct Color {public float r,g,b,a;public Color(float x,float y,float z,float w=1){r=x;g=y;b=z;a=w;}public static Color white{get{return new Color(1,1,1);}}public static Color black{get{return new Color(0,0,0);}}public static Color red{get{return new Color(1,0,0);}}public static Color green{get{return new Color(0,1,0);}}public static Color operator*(Color c,float v){return new Color(c.r*v,c.g*v,c.b*v,c.a*v);}public static Color Lerp(Color a,Color b,float t){return new Color(Mathf.Lerp(a.r,b.r,t),Mathf.Lerp(a.g,b.g,t),Mathf.Lerp(a.b,b.b,t),Mathf.Lerp(a.a,b.a,t));}public static Color HSVToRGB(float h,float s,float v){float hh=h*6;int i=(int)Math.Floor(hh);float f=hh-i,p=v*(1-s),q=v*(1-f*s),t=v*(1-(1-f)*s);switch(i%6){case 0:return new Color(v,t,p);case 1:return new Color(q,v,p);case 2:return new Color(p,v,t);case 3:return new Color(p,q,v);case 4:return new Color(t,p,v);default:return new Color(v,p,q);}}public static void RGBToHSV(Color c,out float h,out float s,out float v){v=Mathf.Max(c.r,Mathf.Max(c.g,c.b));float min=Mathf.Min(c.r,Mathf.Min(c.g,c.b)),d=v-min;s=v==0?0:d/v;h=d==0?0:(v==c.r?(c.g-c.b)/d:(v==c.g?(c.b-c.r)/d+2:(c.r-c.g)/d+4))/6;if(h<0)h++;}}
 public static class Mathf {public const float PI=(float)Math.PI,Rad2Deg=180/PI;public static float Abs(float v){return Math.Abs(v);}public static float Min(float a,float b){return Math.Min(a,b);}public static float Max(float a,float b){return Math.Max(a,b);}public static float Clamp(float v,float a,float b){return Math.Max(a,Math.Min(b,v));}public static int Clamp(int v,int a,int b){return Math.Max(a,Math.Min(b,v));}public static float Clamp01(float v){return Clamp(v,0,1);}public static float Lerp(float a,float b,float t){return a+(b-a)*Clamp01(t);}public static float Exp(float v){return (float)Math.Exp(v);}public static float Sin(float v){return (float)Math.Sin(v);}public static float Cos(float v){return (float)Math.Cos(v);}public static float Pow(float a,float b){return (float)Math.Pow(a,b);}public static float Log(float a){return (float)Math.Log(a);}public static int RoundToInt(float v){return (int)Math.Round(v);}public static int CeilToInt(float v){return (int)Math.Ceiling(v);}public static float MoveTowards(float a,float b,float d){return Math.Abs(b-a)<=d?b:a+Math.Sign(b-a)*d;}}
 public struct Bounds {public Vector3 center,size;public Vector3 extents{get{return size/2;}}public void Expand(float v){size+=Vector3.one*v;}}
 public class Mesh:Object {public Vector3[] vertices=new Vector3[0];public int[] triangles=new int[0];public Color[] colors=new Color[0];public Vector2[] uv;public Bounds bounds;public bool isReadable=true;public int vertexCount{get{return vertices.Length;}}public int blendShapeCount=1;public void MarkDynamic(){}public Mesh Clone(){return new Mesh{name=name,vertices=(Vector3[])vertices.Clone(),triangles=(int[])triangles.Clone(),colors=(Color[])colors.Clone(),uv=uv,bounds=bounds};}public void Clear(){vertices=new Vector3[0];triangles=new int[0];}public void SetVertices(List<Vector3> v){vertices=v.ToArray();}public void SetUVs(int channel,List<Vector2> v){uv=v.ToArray();}public void SetColors(List<Color> v){colors=v.ToArray();}public void SetTriangles(List<int> t,int sub){triangles=t.ToArray();}public void RecalculateNormals(){}public void RecalculateBounds(){if(vertices.Length==0)return;var min=vertices[0];var max=min;foreach(var v in vertices){min=new Vector3(Math.Min(min.x,v.x),Math.Min(min.y,v.y),Math.Min(min.z,v.z));max=new Vector3(Math.Max(max.x,v.x),Math.Max(max.y,v.y),Math.Max(max.z,v.z));}bounds=new Bounds{center=(min+max)/2,size=max-min};}public string GetBlendShapeName(int i){return "Raise_Blind";}public int GetBlendShapeFrameCount(int i){return 1;}public float GetBlendShapeFrameWeight(int i,int frame){return 100;}}
 public class MeshFilter:Component {public Mesh sharedMesh;}
 public class Renderer:Component {public Material sharedMaterial;public Material[] sharedMaterials;public bool enabled=true,receiveShadows;public Bounds bounds;public Rendering.ShadowCastingMode shadowCastingMode;public void SetPropertyBlock(MaterialPropertyBlock b){}}
 public class MeshRenderer:Renderer{}
 public class SkinnedMeshRenderer:Renderer {public Mesh sharedMesh;readonly Dictionary<int,float> weights=new Dictionary<int,float>();public void SetBlendShapeWeight(int i,float v){weights[i]=v;}public float GetBlendShapeWeight(int i){return weights.ContainsKey(i)?weights[i]:0;}public void BakeMesh(Mesh mesh){mesh.vertices=sharedMesh.vertices;}}
 public class Texture:Object{}public class Texture2D:Texture{public static Texture2D whiteTexture=new Texture2D();}
 public class TextAsset:Object{public string text;}
 public class Shader:Object{public static Shader Find(string n){return new Shader();}}
 public class Material:Object {public Color color;public Texture mainTexture;public int renderQueue;public Material(Shader s){}public Material(Material m){}public void SetColor(string n,Color c){}public void SetFloat(string n,float v){}public void SetTexture(string n,Texture t){}public void EnableKeyword(string k){}public void SetOverrideTag(string a,string b){}public bool HasProperty(string p){return true;}}
 public class MaterialPropertyBlock {public void SetColor(string n,Color c){}}
 public class Light:Behaviour {public Color color;public float intensity,range,spotAngle;public LightType type;}
 public enum LightType{Point,Directional,Spot}public enum PrimitiveType{Sphere,Cube}
 public class Collider:Component{public bool isTrigger;}public class BoxCollider:Collider{public Vector3 size;}
 public class Camera:Behaviour {public static Camera main;public bool orthographic;public float orthographicSize,nearClipPlane,farClipPlane,aspect=1;public Rect pixelRect;public Color backgroundColor;public CameraClearFlags clearFlags;public Ray ScreenPointToRay(Vector3 v){return new Ray();}}
 public enum CameraClearFlags{SolidColor}
 public struct Ray{public Vector3 GetPoint(float f){return Vector3.zero;}}public struct RaycastHit{public Collider collider;}
 public struct Plane{public Plane(Vector3 n,Vector3 p){}public bool Raycast(Ray r,out float t){t=0;return true;}}
 public enum QueryTriggerInteraction{Collide}public static class Physics{public static bool Raycast(Ray ray,out RaycastHit hit,float max,int mask,QueryTriggerInteraction q){hit=new RaycastHit();return false;}}
 public static class Time{public static float deltaTime=.016f,time;}
 public static class Input{public static Vector3 mousePosition;public static Vector2 mouseScrollDelta;public static bool GetMouseButton(int i){return false;}public static bool GetMouseButtonDown(int i){return false;}public static bool GetMouseButtonUp(int i){return false;}}
 public struct Rect{public Rect(float x,float y,float w,float h){}}
 public static class Screen{public static int width=1280,height=800;}
 public class GUIStyle{}public class GUISkin{public GUIStyle box=new GUIStyle();}public static class GUI{public static bool enabled=true;public static GUISkin skin=new GUISkin();public static void Box(Rect r,string t){}}
 public static class GUILayout {public static void Label(string t){}public static void Label(string t,GUIStyle s){}public static bool Button(string t){return false;}public static bool Toggle(bool b,string t){return b;}public static float HorizontalSlider(float v,float a,float b){return v;}public static void BeginArea(Rect r){}public static void EndArea(){}public static Vector2 BeginScrollView(Vector2 v){return v;}public static void EndScrollView(){}public static void Space(float v){}public static void BeginHorizontal(){}public static void EndHorizontal(){}}
 public class WaitForSeconds{public WaitForSeconds(float seconds){}}
 public static class Application{public static string unityVersion="OFFLINE_STUB",persistentDataPath=".";}
 public static class Debug{public static void Log(object o){}public static void LogError(object o){}}
 public static class JsonUtility{public static T FromJson<T>(string s){return default(T);}public static string ToJson(object o,bool pretty){return "";}}
 public static class RenderSettings{public static Rendering.AmbientMode ambientMode;public static Color ambientLight;}
 [AttributeUsage(AttributeTargets.Class)]public class RequireComponent:Attribute{public RequireComponent(Type a){}public RequireComponent(Type a,Type b){}}
 [AttributeUsage(AttributeTargets.Field)]public class RangeAttribute:Attribute{public RangeAttribute(float a,float b){}}
}
namespace UnityEngine.Events{public class UnityEvent{public void Invoke(){}}}
namespace UnityEngine.Rendering {public enum ShadowCastingMode{Off}public enum AmbientMode{Flat}public static class GraphicsSettings{public static object currentRenderPipeline;}}
namespace UnityEngine.SceneManagement{public struct Scene{}public static class SceneManager{public static Scene GetActiveScene(){return new Scene();}}}
namespace UnityEditor {
 using UnityEngine;
 [AttributeUsage(AttributeTargets.Method)]public class MenuItem:Attribute{public MenuItem(string s){}}
 [AttributeUsage(AttributeTargets.Class)]public class InitializeOnLoadAttribute:Attribute{}
 public class AssetImporter:Object{public static AssetImporter GetAtPath(string p){return null;}public void SaveAndReimport(){}}
 public class TextureImporter:AssetImporter{public TextureImporterType textureType;public bool alphaIsTransparency;public int maxTextureSize;}
 public enum TextureImporterType{NormalMap,Default}public enum ModelImporterNormals{Import}
 public class ModelImporter:AssetImporter {public float globalScale;public bool useFileScale,bakeAxisConversion,importBlendShapes,isReadable,optimizeGameObjects,preserveHierarchy,importCameras,importLights,importAnimation;public ModelImporterNormals importNormals;}
 public static class AssetDatabase{public static string[] FindAssets(string f,string[] folders=null){return new string[0];}public static string GUIDToAssetPath(string g){return g;}public static T LoadAssetAtPath<T>(string p)where T:Object{return null;}public static bool IsValidFolder(string p){return true;}public static string CreateFolder(string a,string b){return "";}public static void CreateAsset(Object o,string p){}public static void SaveAssets(){}public static void Refresh(){}public static void ImportAsset(string p){}}
 public enum PrefabUnpackMode{Completely}public enum InteractionMode{AutomatedAction}
 public static class PrefabUtility{public static Object InstantiatePrefab(Object o){return o;}public static void UnpackPrefabInstance(GameObject go,PrefabUnpackMode p,InteractionMode i){}public static GameObject SaveAsPrefabAsset(GameObject go,string p,out bool success){success=true;return go;}}
 public static class EditorUtility{public static void CopySerialized(Object a,Object b){}public static void SetDirty(Object o){}}
}
namespace UnityEditor.SceneManagement {
 using UnityEngine.SceneManagement;public enum NewSceneSetup{EmptyScene}public enum NewSceneMode{Single}
 public static class EditorSceneManager{public static bool SaveCurrentModifiedScenesIfUserWantsTo(){return true;}public static Scene NewScene(NewSceneSetup s,NewSceneMode m){return new Scene();}public static bool SaveScene(Scene s,string p){return true;}public static void MarkSceneDirty(Scene s){}}
}
