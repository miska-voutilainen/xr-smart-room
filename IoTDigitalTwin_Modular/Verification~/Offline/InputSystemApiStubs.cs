// Optional compile-only Input System test doubles, NOT the Unity package.
namespace UnityEngine.InputSystem {
 public class AxisControl {public UnityEngine.Vector2 ReadValue(){return UnityEngine.Vector2.zero;}}
 public class ButtonControl {public bool isPressed,wasPressedThisFrame,wasReleasedThisFrame;}
 public class Mouse {public static Mouse current;public AxisControl position=new AxisControl(),scroll=new AxisControl();public ButtonControl leftButton=new ButtonControl(),rightButton=new ButtonControl();}
}
