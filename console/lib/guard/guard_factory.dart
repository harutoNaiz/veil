import 'fake_guard.dart';
import 'guard_client.dart';
import 'pigeon_guard.dart';

/// `--dart-define=VEIL_GUARD=pigeon` selects the bridge; default is the fake.
GuardClient createGuard() {
  const which = String.fromEnvironment('VEIL_GUARD', defaultValue: 'fake');
  return which == 'pigeon' ? PigeonGuard() : FakeGuard();
}
