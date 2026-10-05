import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:veil_console/guard/fake_guard.dart';
import 'package:veil_console/guard/guard_client.dart';
import 'package:veil_console/status/status_screen.dart';

Future<FakeGuard> _up(WidgetTester t) async {
  final g = FakeGuard(statsPeriod: null, granted: Perm.values.toSet());
  await g.connect();
  await g.start();
  await t.pumpWidget(
    MaterialApp(
      home: Scaffold(body: StatusScreen(guard: g)),
    ),
  );
  await t.pumpAndSettle();
  return g;
}

final _resume = find.byKey(const Key('resume-veil'));

void main() {
  var crash = 0, lock = 0, kill = 0;

  testWidgets('crash then Resume x5', (t) async {
    final g = await _up(t);
    for (var i = 0; i < 5; i++) {
      g.simulateCrash();
      await t.pumpAndSettle();
      expect(_resume, findsOneWidget);
      await t.tap(_resume);
      await t.pumpAndSettle();
      expect(g.current.captureState, CaptureState.running);
      expect(g.current.connection, Connection.connected);
      crash++;
    }
  });

  testWidgets('lock then Resume x5', (t) async {
    final g = await _up(t);
    for (var i = 0; i < 5; i++) {
      g.simulateLock();
      await t.pumpAndSettle();
      expect(g.current.captureState, CaptureState.awaitingPermission);
      await t.tap(_resume);
      await t.pumpAndSettle();
      expect(g.current.captureState, CaptureState.running);
      lock++;
    }
  });

  testWidgets('kill switch x5', (t) async {
    final g = await _up(t);
    for (var i = 0; i < 5; i++) {
      await g.stop();
      await t.pumpAndSettle();
      expect(g.current.captureState, CaptureState.stopped);
      expect(g.current.running, isFalse);
      kill++;
      await g.start();
      await t.pumpAndSettle();
      expect(g.current.captureState, CaptureState.running);
    }
  });

  testWidgets('revoking each Perm shows its fix button', (t) async {
    final g = await _up(t);
    for (final p in Perm.values) {
      g.revoke(p);
      await t.pumpAndSettle();
      expect(find.text('Fix'), findsWidgets);
      g.grant(p);
      await t.pumpAndSettle();
    }
  });

  tearDownAll(() {
    // ignore: avoid_print
    print('RECOVERY crash=$crash/5 lock=$lock/5 kill=$kill/5');
  });
}
