using System;using System.Collections.Generic;using System.IO;using System.Linq;
using UnityEngine;using UnityEngine.Rendering;using UnityEditor;using UnityEditor.SceneManagement;using UnityEngine.SceneManagement;
namespace IoTDigitalTwin.Editor {
    [Serializable] public class DeviceAsset {public int id;public string stem,rootName;public Landmark[] anchors;public MaterialDescription[] materials;public RendererDescription[] renderers;}
    [Serializable] public class Landmark {public string name;public Vector3 position;}
    [Serializable] public class RendererDescription {public string name;public string[] materials;}
    [Serializable] public class MaterialDescription {public string name,texture,normalTexture;public Color color,emissionColor;public float roughness,metallic,emission;public bool alphaClip;}
    public static class IoTAssetGenerator {
        public static string Root {get;private set;}
        public static string ActiveDirectory {get;private set;}
        public static string MaterialFolder {get{return ActiveDirectory+"/Materials/Generated";}}
        public static string MeshFolder {get{return ActiveDirectory+"/Prefabs/GeneratedMeshes";}}
        static readonly Dictionary<int,Func<GameObject,IoTDevice>> builders=new Dictionary<int,Func<GameObject,IoTDevice>>();
        public static Action<IoTDevice[]> DemoBuilder;
        public static readonly List<string> results=new List<string>();
        static RuntimeFontAtlas fontAtlas;public static Shader lit,displayShader;
        public static void Register(int id,Func<GameObject,IoTDevice> builder){builders[id]=builder;}
        public static void SetOutputDirectory(string path){ActiveDirectory=path;EnsureFolder(MaterialFolder);EnsureFolder(MeshFolder);}
        public static string TexturePath(string name){string local=ActiveDirectory+"/Textures/"+name;if(File.Exists(local))return local;return Root+"/Shared/Textures/"+name;}
        static Dictionary<int,KeyValuePair<string,DeviceAsset>> Discover(){
            var paths=AssetDatabase.FindAssets("IoTAssetGenerator t:MonoScript").Select(AssetDatabase.GUIDToAssetPath).Where(p=>p.EndsWith("/Shared/Editor/IoTAssetGenerator.cs")).ToArray();Require(paths.Length==1,"Import one IoT asset library copy. Could not uniquely discover Shared/Editor/IoTAssetGenerator.cs.");Root=paths[0].Substring(0,paths[0].Length-"/Shared/Editor/IoTAssetGenerator.cs".Length);
            var found=new Dictionary<int,KeyValuePair<string,DeviceAsset>>();
            foreach(string guid in AssetDatabase.FindAssets("DeviceDefinition t:TextAsset",new[]{Root})){string path=AssetDatabase.GUIDToAssetPath(guid);if(!path.EndsWith("/Materials/DeviceDefinition.json"))continue;var d=JsonUtility.FromJson<DeviceAsset>(File.ReadAllText(path));Require(d.id>=1&&d.id<=9&&!found.ContainsKey(d.id),"Duplicate or invalid device definition: "+path);found[d.id]=new KeyValuePair<string,DeviceAsset>(path.Substring(0,path.Length-"/Materials/DeviceDefinition.json".Length),d);}
            return found;
        }
        [MenuItem("Tools/IoT Digital Twin/Generate Prefabs and Demo")]
        public static void Generate(){if(!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())return;GenerateInternal(0,true);}
        [MenuItem("Tools/IoT Digital Twin/Generate Available Prefabs")]
        public static void GenerateAvailable(){if(!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())return;GenerateInternal(0,false);}
        public static void GenerateDevice(int id){if(!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())return;GenerateInternal(id,false);}
        public static void GenerateBatch(){GenerateInternal(0,true);}
        static void GenerateInternal(int only,bool demo){
            results.Clear();var definitions=Discover();Require(definitions.Count>0,"No device definitions found.");if(demo)Require(definitions.Count==9&&DemoBuilder!=null,"The demo requires all nine devices and Demo. For a partial import use Generate Available Prefabs.");
            lit=Shader.Find(GraphicsSettings.currentRenderPipeline!=null?"Universal Render Pipeline/Lit":"Standard");Require(lit,"Use Built-in or Universal Render Pipeline.");displayShader=Shader.Find("IoTDigitalTwin/Display");Require(displayShader,"Display shader failed to import.");fontAtlas=JsonUtility.FromJson<RuntimeFontAtlas>(File.ReadAllText(Root+"/Shared/Configuration/Runtime_FontAtlas.json"));
            var selected=definitions.Where(p=>only==0||p.Key==only).OrderBy(p=>p.Key).ToArray();Require(selected.Length>0,"Requested device was not imported.");
            foreach(var pair in selected){Require(builders.ContainsKey(pair.Key),"Device builder is missing for device "+pair.Key);string dir=pair.Value.Key;foreach(string texture in Directory.GetFiles(dir+"/Textures","*.png").Concat(Directory.GetFiles(Root+"/Shared/Textures","*.png"))){var ti=(TextureImporter)AssetImporter.GetAtPath(texture.Replace('\\','/'));Require(ti,"Texture importer missing: "+texture);ti.textureType=texture.Contains("Fabric_Normal")?TextureImporterType.NormalMap:TextureImporterType.Default;ti.alphaIsTransparency=!texture.Contains("Fabric_Normal");ti.maxTextureSize=2048;ti.SaveAndReimport();}
                var importer=(ModelImporter)AssetImporter.GetAtPath(dir+"/Models/"+pair.Value.Value.stem+".fbx");Require(importer,"FBX missing: "+dir);importer.globalScale=1;importer.useFileScale=true;importer.bakeAxisConversion=true;importer.importNormals=ModelImporterNormals.Import;importer.importBlendShapes=true;importer.isReadable=pair.Key==5||pair.Key==6;importer.optimizeGameObjects=false;importer.preserveHierarchy=true;importer.importCameras=false;importer.importLights=false;importer.importAnimation=false;importer.SaveAndReimport();}
            Scene scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);var devices=new IoTDevice[9];
            foreach(var pair in selected){var asset=pair.Value.Value;SetOutputDirectory(pair.Value.Key);var wrapper=new GameObject(asset.stem);var imported=AssetDatabase.LoadAssetAtPath<GameObject>(ActiveDirectory+"/Models/"+asset.stem+".fbx");Require(imported,"Model import failed: "+asset.stem);var model=(GameObject)PrefabUtility.InstantiatePrefab(imported);model.transform.SetParent(wrapper.transform,false);PrefabUtility.UnpackPrefabInstance(model,PrefabUnpackMode.Completely,InteractionMode.AutomatedAction);Canonicalize(model,wrapper.transform,asset);AssignMaterials(model,asset);var device=builders[asset.id](wrapper);ValidateDevice(device,asset);devices[asset.id-1]=device;bool success;string path=ActiveDirectory+"/Prefabs/"+asset.stem+".prefab";PrefabUtility.SaveAsPrefabAsset(wrapper,path,out success);Require(success,"Could not save prefab: "+path);results.Add("PASS prefab: "+path);}
            string report=Root+"/Shared/Generator_Verification.txt";
            if(demo){SetOutputDirectory(Root+"/Demo");DemoBuilder(devices);EnsureFolder(Root+"/Demo/Scenes");string scenePath=Root+"/Demo/Scenes/IoT_Interactive_Demo.unity";Require(EditorSceneManager.SaveScene(scene,scenePath),"Could not save demo scene.");results.Add("PASS scene saved: "+scenePath);}
            AssetDatabase.SaveAssets();AssetDatabase.Refresh();File.WriteAllText(report,"Unity "+Application.unityVersion+"\n"+string.Join("\n",results.ToArray())+"\nPlay Mode and manual mouse tests are not run by generation. Run the included Play Mode smoke test and manual checklist.\n");AssetDatabase.ImportAsset(report);Debug.Log("IoT generation completed.\n"+string.Join("\n",results.ToArray()));
        }
        public static void Require(UnityEngine.Object value,string message){if(!value)throw new InvalidOperationException(message);}
        public static void Require(bool value,string message){if(!value)throw new InvalidOperationException(message);}
        public static void EnsureFolder(string path){if(AssetDatabase.IsValidFolder(path))return;int i=path.LastIndexOf('/');EnsureFolder(path.Substring(0,i));AssetDatabase.CreateFolder(path.Substring(0,i),path.Substring(i+1));}
        public static Transform Find(Transform root,string name){foreach(var t in root.GetComponentsInChildren<Transform>(true))if(t.name==name)return t;throw new InvalidOperationException("Required imported part not found: "+name+" under "+root.name);}
        public static T Component<T>(Transform root,string name) where T:Component {var t=Find(root,name);var c=t.GetComponent<T>();Require(c,"Required "+typeof(T).Name+" missing on "+name);return c;}
        public static string Safe(string name){return new string(name.Select(c=>char.IsLetterOrDigit(c)||c=='_'?c:'_').ToArray());}
        public static Material StoreMaterial(Material mat,string key){string folder=key=="FontDisplay"?Root+"/Shared/Materials/Generated":MaterialFolder;EnsureFolder(folder);string path=folder+"/"+Safe(key)+".mat";var old=AssetDatabase.LoadAssetAtPath<Material>(path);if(old){EditorUtility.CopySerialized(mat,old);UnityEngine.Object.DestroyImmediate(mat);EditorUtility.SetDirty(old);return old;}AssetDatabase.CreateAsset(mat,path);return mat;}
        public static Mesh StoreMesh(Mesh mesh,string key){string path=MeshFolder+"/"+key+".asset";var old=AssetDatabase.LoadAssetAtPath<Mesh>(path);if(old){EditorUtility.CopySerialized(mesh,old);UnityEngine.Object.DestroyImmediate(mesh);EditorUtility.SetDirty(old);return old;}AssetDatabase.CreateAsset(mesh,path);return mesh;}
        public static Material BuildMaterial(MaterialDescription d,int id){
            var m=new Material(lit);m.name=d.name;m.SetColor("_Color",d.color);m.SetColor("_BaseColor",d.color);m.SetFloat("_Metallic",d.metallic);m.SetFloat("_Glossiness",1-d.roughness);m.SetFloat("_Smoothness",1-d.roughness);
            if(!string.IsNullOrEmpty(d.texture)){var tex=AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath(d.texture));Require(tex,"Texture missing: "+d.texture);m.SetTexture("_MainTex",tex);m.SetTexture("_BaseMap",tex);}
            if(!string.IsNullOrEmpty(d.normalTexture)){var n=AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath(d.normalTexture));Require(n,"Normal map missing: "+d.normalTexture);m.SetTexture("_BumpMap",n);m.SetFloat("_BumpScale",.65f);m.EnableKeyword("_NORMALMAP");}
            m.EnableKeyword("_EMISSION");m.SetColor("_EmissionColor",d.emissionColor*d.emission);
            if(d.alphaClip){m.SetFloat("_Mode",1);m.SetFloat("_AlphaClip",1);m.SetFloat("_Cutoff",.35f);m.EnableKeyword("_ALPHATEST_ON");m.SetOverrideTag("RenderType","TransparentCutout");m.renderQueue=2450;}
            return StoreMaterial(m,id+"_"+d.name);
        }
        public static void AssignMaterials(GameObject model,DeviceAsset asset){var mats=new Dictionary<string,Material>();foreach(var m in asset.materials)mats[m.name]=BuildMaterial(m,asset.id);foreach(var r in asset.renderers){var renderer=Component<Renderer>(model.transform,r.name);renderer.sharedMaterials=r.materials.Select(n=>mats[n]).ToArray();}results.Add("PASS materials/textures assigned: "+asset.stem);}
        public static Matrix4x4 Basis(Vector3 a,Vector3 b,Vector3 c){var m=Matrix4x4.identity;m.SetColumn(0,new Vector4(a.x,a.y,a.z,0));m.SetColumn(1,new Vector4(b.x,b.y,b.z,0));m.SetColumn(2,new Vector4(c.x,c.y,c.z,0));return m;}
        public static void Canonicalize(GameObject model,Transform frame,DeviceAsset asset){
            Transform sourceRoot=Find(model.transform,asset.rootName);Vector3 origin=sourceRoot.position;Matrix4x4 correction;
            if(asset.anchors.Length==3){
                Vector3 a=Find(model.transform,asset.anchors[0].name).position-origin,b=Find(model.transform,asset.anchors[1].name).position-origin,c=Find(model.transform,asset.anchors[2].name).position-origin;
                Matrix4x4 actual=Basis(a,b,c);Require(Mathf.Abs(actual.determinant)>1e-12f,"Degenerate FBX calibration landmarks: "+asset.stem);
                correction=Basis(asset.anchors[0].position,asset.anchors[1].position,asset.anchors[2].position)*actual.inverse;
            }else{
                bool dimmer=asset.id==1;Vector3 forward=Find(model.transform,dimmer?"05_Rotary_Knob":"Wall_Mount_Plate").position-origin;float scale=(dimmer?.010f:.002f)/forward.magnitude;Vector3 label=Find(model.transform,dimmer?"06_Removable_Installation_Label":"Sliding_Drive_Cover").position-origin;
                Vector3 up=(dimmer?-1:1)*(label-Vector3.Project(label,forward));Require(up.sqrMagnitude>1e-9f,"Dimmer orientation landmarks missing.");Quaternion rotation=Quaternion.Inverse(Quaternion.LookRotation(forward,up));correction=Matrix4x4.TRS(Vector3.zero,rotation,Vector3.one*scale);
            }
            Vector3 translation=-correction.MultiplyVector(origin);correction.SetColumn(3,new Vector4(translation.x,translation.y,translation.z,1));Matrix4x4 composed=correction*model.transform.localToWorldMatrix;
            Vector3 x=composed.GetColumn(0),y=composed.GetColumn(1),z=composed.GetColumn(2);Vector3 scale3=new Vector3(x.magnitude,y.magnitude,z.magnitude);if(composed.determinant<0)scale3.x=-scale3.x;
            model.transform.localPosition=composed.GetColumn(3);model.transform.localRotation=Quaternion.LookRotation(z,y);model.transform.localScale=scale3;
            foreach(var anchor in asset.anchors){Vector3 p=frame.InverseTransformPoint(Find(model.transform,anchor.name).position);Require((p-anchor.position).magnitude<.0002f,"Scale/pivot calibration mismatch: "+anchor.name);}
            Require(frame.InverseTransformPoint(sourceRoot.position).magnitude<.0002f,"Mounting root is not at the origin: "+asset.stem);results.Add("PASS metre scale and axis landmarks: "+asset.stem);
        }
        public static Vector3 Photo(float x,float z,float depth){return new Vector3(-x,z,depth);}
        public static void Target(IoTDevice device,Transform follow,string action,Vector3 canonical,float width,float height){
            var go=new GameObject("Input_"+action);go.transform.SetParent(follow,false);go.transform.position=device.transform.TransformPoint(canonical);go.transform.rotation=device.transform.rotation;
            var box=go.AddComponent<BoxCollider>();box.size=new Vector3(width,height,.002f);box.isTrigger=true;
            var target=go.AddComponent<DevicePointerTarget>();target.device=device;target.action=action;target.width=width;target.height=height;
        }
        public static void TargetBounds(IoTDevice device,string part,string action,float width,float height,float depthOffset=.001f){var t=Find(device.transform,part);var r=t.GetComponent<Renderer>();Vector3 p=device.transform.InverseTransformPoint(r.bounds.center);p.z+=r.bounds.extents.z+depthOffset;Target(device,t,action,p,width,height);}
        public static DynamicReadout Text(Transform frame,string name,string content,Vector3 position,float height,Color color){
            var go=new GameObject(name);go.transform.SetParent(frame,false);go.transform.localPosition=position;go.transform.localRotation=Quaternion.Euler(0,180,0);var filter=go.AddComponent<MeshFilter>();var renderer=go.AddComponent<MeshRenderer>();var m=new Material(displayShader);m.mainTexture=AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath(fontAtlas.texture));Require(m.mainTexture,"Glyph atlas texture is missing.");renderer.sharedMaterial=StoreMaterial(m,"FontDisplay");renderer.shadowCastingMode=ShadowCastingMode.Off;renderer.receiveShadows=false;
            var text=go.AddComponent<DynamicReadout>();text.glyphs=fontAtlas.glyphs;text.height=height;text.referencePixels=content.Any(char.IsDigit)?fontAtlas.digitHeight:fontAtlas.capitalHeight;text.tint=color;text.SetText(content);filter.sharedMesh=StoreMesh(text.PreviewMesh,"Text_"+name);text.ReleaseEditorOwnership();return text;
        }
        public static void ReplaceScreen(Transform frame,string part,string texture){var renderer=Component<Renderer>(frame,part);var m=new Material(renderer.sharedMaterial);var image=AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath(texture));Require(image,"Runtime screen background missing.");m.SetTexture("_MainTex",image);m.SetTexture("_BaseMap",image);if(m.HasProperty("_EmissionColor")){m.SetColor("_EmissionColor",Color.black);}renderer.sharedMaterial=StoreMaterial(m,"Runtime_"+part);}
        public static Transform Sprite(Transform frame,string name,Vector3 position,float w,float h,string texture){
            var go=new GameObject(name);go.transform.SetParent(frame,false);go.transform.localPosition=position;var mesh=new Mesh();mesh.name=name;mesh.vertices=new[]{new Vector3(w/2,-h/2,0),new Vector3(-w/2,-h/2,0),new Vector3(-w/2,h/2,0),new Vector3(w/2,h/2,0)};mesh.uv=new[]{new Vector2(0,0),new Vector2(1,0),new Vector2(1,1),new Vector2(0,1)};mesh.colors=new[]{Color.white,Color.white,Color.white,Color.white};mesh.triangles=new[]{0,1,2,0,2,3};mesh.RecalculateNormals();mesh.RecalculateBounds();go.AddComponent<MeshFilter>().sharedMesh=StoreMesh(mesh,name);var renderer=go.AddComponent<MeshRenderer>();var m=new Material(displayShader);m.mainTexture=AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath(texture));renderer.sharedMaterial=StoreMaterial(m,name);renderer.shadowCastingMode=ShadowCastingMode.Off;return go.transform;
        }
        public static Indicator Ind(Transform root,string name){return new Indicator{renderer=Component<Renderer>(root,name)};}
        public static PressPart Press(Transform root,string name){return new PressPart{part=Find(root,name)};}
        public static Vector3 DaliPixel(float x,float y){return Photo(-.078f+x/1600*.156f,.044f-y/900*.088f,.02245f);}
        public static BeadChainMotion Chain(Transform frame,string part,bool side,float top,float bottom,float radius,float depth,float xOffset){
            MeshFilter filter=Component<MeshFilter>(frame,part);Mesh mesh=filter.sharedMesh;Require(mesh.isReadable,"Bead mesh must be readable: "+part);Vector3[] vertices=mesh.vertices;int[] indices=mesh.triangles;var union=new UnionFind(vertices.Length);var welded=new Dictionary<string,int>();
            for(int i=0;i<vertices.Length;i++){Vector3 v=vertices[i];string key=Mathf.RoundToInt(v.x*1000000)+","+Mathf.RoundToInt(v.y*1000000)+","+Mathf.RoundToInt(v.z*1000000);int other;if(welded.TryGetValue(key,out other))union.Join(i,other);else welded.Add(key,i);}
            for(int i=0;i<indices.Length;i+=3){union.Join(indices[i],indices[i+1]);union.Join(indices[i],indices[i+2]);}
            var groups=new Dictionary<int,List<int>>();for(int i=0;i<vertices.Length;i++){int key=union.Find(i);if(!groups.ContainsKey(key))groups[key]=new List<int>();groups[key].Add(i);}
            Require(groups.Count>=20&&groups.Count<500,"Unexpected bead island count: "+part+" = "+groups.Count);
            var islands=new List<ChainIsland>();
            foreach(var group in groups.Values){var unique=new Dictionary<string,Vector3>();foreach(int i in group){Vector3 v=vertices[i];string key=Mathf.RoundToInt(v.x*1000000)+","+Mathf.RoundToInt(v.y*1000000)+","+Mathf.RoundToInt(v.z*1000000);unique[key]=v;}Vector3 centre=Vector3.zero;foreach(var v in unique.Values)centre+=v;centre/=unique.Count;Vector3 p=frame.InverseTransformPoint(filter.transform.TransformPoint(centre));double horizontal=side?depth-p.z:-p.x;islands.Add(new ChainIsland{indices=group.ToArray(),centre=centre,arcDistance=DeviceMath.CapsuleDistance(horizontal,p.y,top,bottom,radius)});}
            var motion=filter.gameObject.AddComponent<BeadChainMotion>();motion.frame=frame;motion.filter=filter;motion.islands=islands.ToArray();motion.sidePlane=side;motion.top=top;motion.bottom=bottom;motion.radius=radius;motion.depth=depth;motion.xOffset=xOffset;results.Add("PASS "+part+": "+islands.Count+" welded bead islands, one animated mesh");return motion;
        }
        public static void ValidateDevice(IoTDevice device,DeviceAsset asset){
            int[] counts={1,4,5,2,3,1,2,2,8};var targets=device.GetComponentsInChildren<DevicePointerTarget>(true);Require(targets.Length==counts[asset.id-1],"Incorrect pointer target count: "+asset.stem);foreach(var target in targets){Require(target.device==device,"Unbound target "+target.name);Require(target.GetComponent<BoxCollider>(),"Missing collider "+target.name);}
            foreach(var renderer in device.GetComponentsInChildren<Renderer>(true))foreach(var material in renderer.sharedMaterials)Require(material,"Missing material on "+renderer.name);

            results.Add("PASS references/colliders and "+targets.Length+" controls: "+asset.stem);
        }
        [MenuItem("Tools/IoT Digital Twin/Add Mouse Input to Current Scene")]
        public static void AddInput(){if(UnityEngine.Object.FindObjectOfType<IoTMouseInput>())return;Require(Camera.main,"Tag your interaction camera MainCamera first.");var input=Camera.main.gameObject.AddComponent<IoTMouseInput>();input.interactionCamera=Camera.main;EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());}
    }
}
