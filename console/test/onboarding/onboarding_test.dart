import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:veil_console/app.dart';
import 'package:veil_console/guard/fake_guard.dart';
import 'package:veil_console/guard/guard_client.dart';
import 'package:veil_console/status/status_screen.dart';

Widget _app(GuardClient g) => VeilConsoleApp(
  guard: g,
  homeBuilder: (_) => const Scaffold(body: Text('HOME')),
);

void main() {
  testWidgets('full onboarding reaches home; every Perm requested in order', (
    tester,
  ) async {
    final g = FakeGuard(statsPeriod: null);
    await tester.pumpWidget(_app(g));
    await tester.pumpAndSettle();
    for (var i = 0; i < Perm.values.length; i++) {
      await tester.tap(find.byType(FilledButton));
      await tester.pumpAndSettle();
    }
    expect(find.text('Veil is ready'), findsOneWidget);
    await tester.tap(find.text('Start using Veil'));
    await tester.pumpAndSettle();
    expect(find.text('HOME'), findsOneWidget);
    final reqs = g.calls.where((c) => c.contains('requestPermission')).toList();
    expect(reqs.length, Perm.values.length);
  });

  testWidgets('StatusScreen shows 3 Fix buttons; tap fixes row', (
    tester,
  ) async {
    final g = FakeGuard(
      statsPeriod: null,
      granted: {Perm.disclosure, Perm.accessibility},
    );
    await g.connect();
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: StatusScreen(guard: g)),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Fix'), findsNWidgets(3));
    await tester.tap(find.text('Fix').first);
    await tester.pumpAndSettle();
    expect(find.text('Fix'), findsNWidgets(2));
    expect(find.byIcon(Icons.check_circle), findsNWidgets(3));
  });

  testWidgets('incompatible version shows update screen', (tester) async {
    await tester.pumpWidget(
      _app(FakeGuard(protocolVersion: 99, statsPeriod: null)),
    );
    await tester.pumpAndSettle();
    expect(find.text('Update Veil'), findsOneWidget);
  });

  testWidgets('a11y guidelines on every onboarding page', (tester) async {
    final handle = tester.ensureSemantics();
    final g = FakeGuard(statsPeriod: null);
    await tester.pumpWidget(_app(g));
    await tester.pumpAndSettle();
    for (var i = 0; i <= Perm.values.length; i++) {
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      if (i < Perm.values.length) {
        await tester.tap(find.byType(FilledButton));
        await tester.pumpAndSettle();
      }
    }
    handle.dispose();
  });

  testWidgets('200% text scale: no overflow on any page', (tester) async {
    final g = FakeGuard(statsPeriod: null);
    await tester.pumpWidget(
      MediaQuery(
        data: const MediaQueryData(textScaler: TextScaler.linear(2.0)),
        child: _app(g),
      ),
    );
    await tester.pumpAndSettle();
    for (var i = 0; i < Perm.values.length; i++) {
      expect(tester.takeException(), isNull);
      await tester.tap(find.byType(FilledButton));
      await tester.pumpAndSettle();
    }
    expect(tester.takeException(), isNull);
  });

  testWidgets('dark brightness renders', (tester) async {
    tester.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
    addTearDown(tester.platformDispatcher.clearAllTestValues);
    await tester.pumpWidget(_app(FakeGuard(statsPeriod: null)));
    await tester.pumpAndSettle();
    expect(
      Theme.of(tester.element(find.byType(Scaffold).first)).brightness,
      Brightness.dark,
    );
    expect(tester.takeException(), isNull);
  });
}
