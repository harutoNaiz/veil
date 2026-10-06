import 'dart:io';

import 'fake_guard.dart';
import 'guard_client.dart';
import 'pigeon_guard.dart';

/// Real bridge on an Android device; FakeGuard in tests and on other platforms.
/// `--dart-define=VEIL_GUARD=fake|pigeon` overrides.
GuardClient createGuard() {
  const which = String.fromEnvironment('VEIL_GUARD');
  if (which == 'fake') return FakeGuard();
  if (which == 'pigeon') return PigeonGuard();
  final inTest = Platform.environment.containsKey('FLUTTER_TEST');
  return Platform.isAndroid && !inTest ? PigeonGuard() : FakeGuard();
}
