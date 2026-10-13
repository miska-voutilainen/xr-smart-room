using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
namespace IoTDigitalTwin {
    [Serializable] public class SmokeRecord {public string interaction;public bool passed;public string detail;}
    [Serializable] public class SmokeReport {public string unityVersion;public bool actualUnityPlayMode=true,mouseInteractionsTested=false;public SmokeRecord[] tests;}
    public sealed class IoTPlayModeSmokeTest:MonoBehaviour {
        public IoTDevice[] devices;public bool Running{get;private set;}public string Summary{get;private set;}
        readonly List<SmokeRecord> records=new List<SmokeRecord>();
        public void Begin(){if(!Running)StartCoroutine(Run());}
        void Check(string name,Action action){try{action();records.Add(new SmokeRecord{interaction=name,passed=true,detail="Passed in Unity Play Mode"});}catch(Exception e){records.Add(new SmokeRecord{interaction=name,passed=false,detail=e.Message});Debug.LogError(name+": "+e);}}
        static void Assert(bool value,string message){if(!value)throw new InvalidOperationException(message);}
        IEnumerator Run(){
            Running=true;records.Clear();var demo=GetComponent<IoTDemoController>();bool auto=demo.automaticReadings,connected=demo.connectAqara;demo.automaticReadings=false;demo.connectAqara=false;
            var d=(RotaryDimmer)devices[0];var s=(TemperatureLCD)devices[1];var t=(TemperatureController)devices[2];var c=(SecurityCameraDevice)devices[3];var a=(AqaraChainController)devices[4];var b=(RollerBlindDevice)devices[5];var n=(SiemensBACnetDevice)devices[6];var sp=(NestSpeakerDevice)devices[7];var p=(DALILightingPanel)devices[8];
            float oldBrightness=d.Brightness,oldTemp=s.Temperature,oldHumidity=s.Humidity,oldMeasured=t.Temperature,oldTarget=t.TargetTemperature,oldTilt=c.Tilt,oldYaw=c.Yaw,oldA=a.OpenPercent,oldBlind=b.TargetOpenPercent,oldNumber=n.DisplayValue,oldVolume=sp.Volume,oldPanelBrightness=p.Brightness,oldKelvin=p.ColorTemperature;
            bool oldDimmerPower=d.Power,oldThermostatPower=t.Power,oldCameraPower=c.Power,oldFlood=c.Floodlight,oldCover=a.coverOpen,oldStatus=n.Status,oldMuted=sp.Muted,oldActive=sp.Active,oldPanelPower=p.Power,oldUseTemperature=p.useTemperature;
            Color oldColor=p.selectedColor;int oldScene=p.sceneIndex;float blindSpeed=b.percentPerSecond,driveSpeed=a.percentPerSecond;ThermostatMode oldMode=t.mode;Vector3 knobPivot=d.knob.position;
            try {
                Check("Dimmer public controls",()=>{d.SetBrightness(.75f);d.SetPower(true);Assert(d.Brightness==.75f&&d.Power,"Dimmer state did not update.");});
                Check("Live LCD temperature/humidity",()=>{s.SetTemperature(29);s.SetHumidity(67);Assert(s.temperatureText.Value.Contains("29.0")&&s.humidityText.Value.Contains("67"),"LCD text did not update.");});
                Check("Thermostat target/mode/power",()=>{t.SetTemperature(24);t.SetTargetTemperature(30);t.SetMode(ThermostatMode.Heat);t.SetPower(false);Assert(t.TargetTemperature==30&&t.stateText.Value=="OFF","Thermostat display did not update.");});
                Check("Camera tilt/yaw/flood state",()=>{c.SetTilt(20);c.SetYaw(15);c.SetPower(true);c.SetFloodlight(true);Assert(c.Tilt==20&&c.Yaw==15&&c.Power&&c.Floodlight,"Camera commands not reflected.");});
                yield return new WaitForSeconds(.35f);
                Check("Dimmer pivot retained",()=>Assert((d.knob.position-knobPivot).magnitude<.00001f,"Knob rotated around the wrong pivot."));
                Check("Camera emitted floodlight",()=>Assert(c.flood.light&&c.flood.light.enabled&&c.flood.light.intensity>0,"Floodlight did not illuminate."));
                a.ConnectBlind(null);a.percentPerSecond=200;Vector3[] before=a.chain.filter.sharedMesh.vertices;a.SetOpenPercent(100);a.SetCoverOpen(true);
                yield return new WaitForSeconds(.3f);
                Check("Aqara standalone drive and bead motion",()=>{Assert(a.OpenPercent>0,"Standalone drive did not advance.");Vector3[] after=a.chain.filter.sharedMesh.vertices;bool moved=false;for(int i=0;i<after.Length;i++)if((after[i]-before[i]).sqrMagnitude>1e-10f){moved=true;break;}Assert(moved,"Bead mesh remained stationary.");a.Stop();Assert(Mathf.Abs(a.targetOpenPercent-a.OpenPercent)<.001f,"Aqara Stop did not hold its current position.");});
                b.percentPerSecond=200;b.Open();yield return new WaitForSeconds(.65f);
                Check("Blind fully open and synchronized",()=>{Assert(Mathf.Abs(b.OpenPercent-100)<.001f,"Blind did not reach 100%.");Assert(Mathf.Abs(b.cloth.GetBlendShapeWeight(b.blendShapeIndex)-b.fullyRaisedWeight)<.01f,"Cloth weight mismatch.");float y=b.transform.InverseTransformPoint(b.bottomRail.position).y;Assert(Mathf.Abs(y+.05875f)<.0002f,"Raised rail position mismatch.");CheckClothRail(b);});
                b.Close();yield return new WaitForSeconds(.65f);
                Check("Blind fully closed and synchronized",()=>{Assert(b.OpenPercent<.001f,"Blind did not reach 0%.");CheckClothRail(b);});
                b.Open();yield return new WaitForSeconds(.15f);b.Stop();float stopped=b.OpenPercent;yield return new WaitForSeconds(.15f);
                Check("Blind Stop",()=>Assert(Mathf.Abs(stopped-b.OpenPercent)<.001f,"Blind moved after Stop."));
                Check("Live LED digits and status",()=>{n.SetDisplayValue(42);n.SetStatus(false);Assert(n.DisplayValue==42&&!n.Status,"BACnet state mismatch.");Assert(n.display.filter.sharedMesh.colors.Length>0,"Dynamic LED mesh has no colours.");});
                Check("Speaker controls",()=>{sp.SetVolume(.9f);sp.SetMuted(true);sp.SetActive(true);Assert(sp.Volume==.9f&&sp.Muted&&sp.Active,"Speaker state mismatch.");});
                Check("DALI lighting API and dynamic interface",()=>{p.SetPower(true);p.SetBrightness(.65f);p.SetColor(Color.red);Assert(p.SelectedColor.r>.99f&&p.SelectedColor.g<.01f,"RGB colour not set.");p.SetColorTemperature(5800);Assert(p.ColorTemperature==5800&&p.useTemperature,"Kelvin state not set.");p.SelectScene(2);Assert(p.sceneIndex==2&&p.percentText.Value=="15%","Preset/UI mismatch.");});
                yield return new WaitForSeconds(.1f);
                Check("Input bindings exist for all devices",()=>{foreach(var device in devices){var targets=device.GetComponentsInChildren<DevicePointerTarget>();Assert(targets.Length>0,"No mouse controls: "+device.name);foreach(var target in targets)Assert(target.device==device&&target.GetComponent<Collider>(),"Broken target reference.");}});
            } finally {
                d.SetBrightness(oldBrightness);d.SetPower(oldDimmerPower);s.SetTemperature(oldTemp);s.SetHumidity(oldHumidity);t.SetTemperature(oldMeasured);t.SetTargetTemperature(oldTarget);t.SetMode(oldMode);t.SetPower(oldThermostatPower);c.SetTilt(oldTilt);c.SetYaw(oldYaw);c.SetPower(oldCameraPower);c.SetFloodlight(oldFlood);a.SetCoverOpen(oldCover);a.SetOpenPercent(oldA);a.percentPerSecond=driveSpeed;b.SetOpenPercent(oldBlind);b.percentPerSecond=blindSpeed;n.SetDisplayValue(oldNumber);n.SetStatus(oldStatus);sp.SetVolume(oldVolume);sp.SetMuted(oldMuted);sp.SetActive(oldActive);p.SetBrightness(oldPanelBrightness);if(oldUseTemperature)p.SetColorTemperature(oldKelvin);else p.SetColor(oldColor);p.sceneIndex=oldScene;p.SetPower(oldPanelPower);demo.automaticReadings=auto;demo.connectAqara=connected;Running=false;
            }
            int passed=0;foreach(var r in records)if(r.passed)passed++;Summary=passed+" / "+records.Count+" API checks passed. Mouse tests remain manual.";string path=Path.Combine(Application.persistentDataPath,"IoT_PlayMode_Verification.json");File.WriteAllText(path,JsonUtility.ToJson(new SmokeReport{unityVersion=Application.unityVersion,tests=records.ToArray()},true));Debug.Log(Summary+" Report: "+path);
        }
        static void CheckClothRail(RollerBlindDevice b){var baked=new Mesh();try{b.cloth.BakeMesh(baked);float bottom=float.PositiveInfinity;foreach(var v in baked.vertices){float y=b.transform.InverseTransformPoint(b.cloth.transform.TransformPoint(v)).y;bottom=Mathf.Min(bottom,y);}float rail=b.transform.InverseTransformPoint(b.bottomRail.position).y;Assert(Mathf.Abs(bottom-rail)<.002f,"Cloth bottom and rail disconnect.");}finally{UnityEngine.Object.Destroy(baked);}}
    }
}
