import '../guard/guard_client.dart';

class PermInfo {
  final String title;
  final String reason;
  final String action;
  const PermInfo(this.title, this.reason, this.action);
}

const Map<Perm, PermInfo> permInfo = {
  Perm.disclosure: PermInfo(
    'Your consent',
    'Veil needs your agreement before it starts watching the screen.',
    'I agree',
  ),
  Perm.accessibility: PermInfo(
    'Accessibility service',
    'Lets Veil place a cover over content on your screen.',
    'Open settings',
  ),
  Perm.restrictedSettings: PermInfo(
    'Allow restricted settings',
    'Android blocks sideloaded apps from using accessibility until you allow it.',
    'Open settings',
  ),
  Perm.screenCapture: PermInfo(
    'Screen capture',
    'Lets Veil look at what is on screen. Android asks again after the phone locks.',
    'Allow',
  ),
  Perm.notifications: PermInfo(
    'Notifications',
    'Lets you tap "Resume Veil" after a pause.',
    'Allow',
  ),
};
