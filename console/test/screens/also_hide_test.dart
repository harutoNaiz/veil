import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:veil_console/guard/fake_guard.dart';
import 'package:veil_console/guard/guard_client.dart';
import 'package:veil_console/screens/concept_studio_screen.dart';

void main() {
  testWidgets('also hide: type, pick a chip, add', (t) async {
    final fake = FakeGuard(statsPeriod: null);
    await fake.connect();
    await t.pumpWidget(
      MaterialApp(
        home: Scaffold(body: ConceptStudioScreen(guard: fake)),
      ),
    );
    await t.enterText(find.byType(TextField), 'buffalo');
    await t.pump();
    await t.pump();
    expect(find.text('Also hide:'), findsOneWidget);
    expect(find.byType(FilterChip), findsNWidgets(6));
    expect(find.textContaining('Active in'), findsOneWidget);
    await t.tap(find.widgetWithText(FilterChip, 'bison'));
    await t.pump();
    await t.ensureVisible(find.text('Add'));
    await t.runAsync(() async {
      await t.tap(find.text('Add'));
      await Future<void>.delayed(const Duration(milliseconds: 500));
    });
    await t.pump();
    final c = fake.current.concepts.single;
    expect(c.alsoHide, ['bison']);
    expect(c.butNot, contains('yak'));
    expect(c.butNot, isNot(contains('bison')));
    final p = await fake.previewWord('buffalo');
    expect(p.elapsedMs, lessThan(1000));
  });
}
