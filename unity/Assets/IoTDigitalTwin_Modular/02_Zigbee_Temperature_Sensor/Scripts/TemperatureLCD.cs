using UnityEngine;
namespace IoTDigitalTwin {
    public sealed class TemperatureLCD:IoTDevice {
        public float temperature=21.7f,humidity=48;public bool editHumidity;
        public DynamicReadout temperatureText,humidityText,pairingText;public PressPart[] buttons;
        float pairingUntil;bool pairingLast;
        public float Temperature{get{return temperature;}}public float Humidity{get{return humidity;}}
        void Awake(){foreach(var p in buttons)p.Capture(transform,.0004f);Refresh();}
        public void SetTemperature(float value){temperature=DeviceMath.ClampFinite(value,-40,80);Refresh();Notify();}
        public void SetHumidity(float value){humidity=DeviceMath.ClampFinite(value,0,100);Refresh();Notify();}
        public void SetPairing(bool enabled){pairingUntil=enabled?Time.time+5:0;Refresh();Notify();}
        void Refresh(){temperatureText.SetText(temperature.ToString("0.0",System.Globalization.CultureInfo.InvariantCulture)+"°C");humidityText.SetText(humidity.ToString("0",System.Globalization.CultureInfo.InvariantCulture)+"%");pairingText.SetText(Time.time<pairingUntil?"PAIR":"");}
        void Update(){foreach(var p in buttons)p.Apply(Time.deltaTime);bool pairing=Time.time<pairingUntil;if(pairing!=pairingLast){pairingLast=pairing;Refresh();}}
        public override void Control(string action,Vector2 uv){
            if(action=="Plus"){buttons[0].Press();if(editHumidity)SetHumidity(humidity+1);else SetTemperature(temperature+.5f);}
            else if(action=="Minus"){buttons[2].Press();if(editHumidity)SetHumidity(humidity-1);else SetTemperature(temperature-.5f);}
            else if(action=="Mode"){buttons[1].Press();editHumidity=!editHumidity;humidityText.SetColor(editHumidity?new Color(.05f,.17f,.05f):new Color(.08f,.12f,.07f));Notify();}
            else if(action=="Pair")SetPairing(Time.time>=pairingUntil);
        }
    }
}
