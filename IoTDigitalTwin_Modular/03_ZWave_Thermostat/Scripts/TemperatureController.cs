using UnityEngine;
namespace IoTDigitalTwin {
    public enum ThermostatMode{Auto,Heat,Cool}
    public sealed class TemperatureController:IoTDevice {
        public float temperature=22.6f,targetTemperature=22;public bool power=true,schedule;
        public ThermostatMode mode;
        public DynamicReadout measuredText,targetText,stateText,modeText;
        public float Temperature{get{return temperature;}}public float TargetTemperature{get{return targetTemperature;}}public bool Power{get{return power;}}
        void Awake(){Refresh();}
        public void SetTemperature(float value){temperature=DeviceMath.ClampFinite(value,-40,80);Refresh();Notify();}
        public void SetTargetTemperature(float value){targetTemperature=DeviceMath.ClampFinite(value,5,35);Refresh();Notify();}
        public void SetPower(bool value){power=value;Refresh();Notify();}
        public void SetMode(ThermostatMode value){mode=value;Refresh();Notify();}
        void Refresh(){measuredText.SetText(power?temperature.ToString("0.0",System.Globalization.CultureInfo.InvariantCulture)+"°C":"--.-");targetText.SetText("SET "+targetTemperature.ToString("0.0",System.Globalization.CultureInfo.InvariantCulture));stateText.SetText(power?"ON":"OFF");modeText.SetText(mode.ToString().ToUpperInvariant()+(schedule?"  SCHEDULE":""));}
        public override void Control(string action,Vector2 uv){
            switch(action){case "Up":SetTargetTemperature(targetTemperature+.5f);break;case "Down":SetTargetTemperature(targetTemperature-.5f);break;case "Power":SetPower(!power);break;case "Mode":SetMode((ThermostatMode)(((int)mode+1)%3));break;case "Schedule":schedule=!schedule;Refresh();Notify();break;}
        }
    }
}
