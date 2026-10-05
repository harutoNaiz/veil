import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:veil_console/guard/fake_guard.dart';
import 'package:veil_console/guard/guard_client.dart';
import 'package:veil_console/screens/home_shell.dart';

FakeGuard newFake() =>
    FakeGuard(granted: Perm.values.toSet(), statsPeriod: null);

Future<void> pumpShell(
  WidgetTester t,
  FakeGuard fake, {
  Brightness brightness = Brightness.light,
  double scale = 1.0,
  PhotoSource? photos,
}) async {
  await t.pumpWidget(
    MaterialApp(
      theme: ThemeData(brightness: brightness),
      builder: (c, child) => MediaQuery(
        data: MediaQuery.of(c).copyWith(textScaler: TextScaler.linear(scale)),
        child: child!,
      ),
      home: HomeShell(guard: fake, photos: photos),
    ),
  );
  await t.pump();
}

Future<void> goTo(WidgetTester t, String label) async {
  await t.tap(
    find.descendant(of: find.byType(NavigationBar), matching: find.text(label)),
  );
  await t.pump(const Duration(milliseconds: 300));
}

const labels = ['Concepts', 'Strictness', 'Skip list', 'Stats', 'Recent'];

void main() {
  late FakeGuard fake;
  setUp(() async {
    fake = newFake();
    await fake.connect();
  });

  testWidgets('start/stop switch calls the Guard', (t) async {
    await pumpShell(t, fake);
    await t.tap(find.byType(Switch));
    await t.pump();
    expect(fake.calls, contains('start'));
    expect(fake.current.running, isTrue);
    await t.tap(find.byType(Switch));
    await t.pump();
    expect(fake.calls, contains('stop'));
  });

  testWidgets('concept studio: compile, save, toggle, rejected pack', (
    t,
  ) async {
    final photo = FileRef('x.jpg', 'ab');
    await pumpShell(t, fake, photos: FakePhotoSource([photo]));
    await t.enterText(find.byType(TextField), 'cats');
    await t.tap(find.text('Add example photo'));
    await t.pump();
    await t.tap(find.text('Preview'));
    await t.pump();
    expect(fake.calls, contains('compileConcept'));
    expect(find.text('Looks like'), findsOneWidget);
    expect(find.text('But not'), findsOneWidget);
    await t.tap(find.text('Mosaic'));
    await t.pump();
    await t.ensureVisible(find.text('Save'));
    await t.runAsync(() async {
      await t.tap(find.text("Save"));
      await Future<void>.delayed(const Duration(milliseconds: 500));
    });
    await t.pump();
    expect(fake.calls, contains('applyConcepts'));
    expect(fake.current.concepts, hasLength(1));
    expect(fake.current.concepts.first.coverStyle, CoverStyle.mosaic);
    expect(fake.current.concepts.first.examplePhotos, hasLength(1));
    await t.pump();
    await t.ensureVisible(find.byType(SwitchListTile));
    await t.runAsync(() async {
      await t.tap(find.byType(SwitchListTile));
      await Future<void>.delayed(const Duration(milliseconds: 500));
    });
    await t.pump();
    expect(fake.current.concepts.first.enabled, isFalse);
    expect(fake.calls.where((c) => c == 'applyConcepts').length, 2);
  });

  testWidgets('strictness: radio calls setMode', (t) async {
    await pumpShell(t, fake);
    await goTo(t, 'Strictness');
    await t.tap(find.text('Strict'));
    await t.pump();
    expect(fake.calls, contains('setMode'));
    expect(fake.current.mode, Mode.strict);
  });

  testWidgets('skip list: checkbox calls setSkipList', (t) async {
    await pumpShell(t, fake);
    await goTo(t, 'Skip list');
    await t.pump();
    await t.tap(find.byType(CheckboxListTile).first);
    await t.pump();
    expect(fake.calls, contains('installedApps'));
    expect(fake.calls, contains('setSkipList'));
    expect(fake.current.skipList, hasLength(1));
  });

  testWidgets('stats: dash until first tick, then updates', (t) async {
    await pumpShell(t, fake);
    await goTo(t, 'Stats');
    expect(find.text('—'), findsNWidgets(4));
    fake.emitStats(
      const StatsTick(
        tMs: 1,
        looksPerSecond: 4.5,
        aiMsLastLook: 12.0,
        batteryImpactPctPerHour: 2.5,
        activeCovers: 3,
      ),
    );
    await t.pump();
    await t.pump();
    expect(find.text('4.5'), findsOneWidget);
    expect(find.text('12.0'), findsOneWidget);
    expect(find.text('2.5'), findsOneWidget);
    expect(find.text('3'), findsOneWidget);
  });

  testWidgets('recent covers: feedback buttons call submitFeedback', (t) async {
    await pumpShell(t, fake);
    await goTo(t, 'Recent');
    await t.pump();
    await t.tap(find.text('Not this').first);
    await t.pump();
    expect(fake.calls, contains('recentCovers'));
    expect(fake.calls, contains('submitFeedback'));
    expect(find.text('Not this ✓'), findsOneWidget);
    await t.tap(find.text('Correct').first);
    await t.tap(find.text('Missed one').first);
    await t.pump();
    expect(fake.calls.where((c) => c == 'submitFeedback').length, 3);
  });

  testWidgets('reopen: strict mode shown by a fresh HomeShell', (t) async {
    await pumpShell(t, fake);
    await goTo(t, 'Strictness');
    await t.tap(find.text('Strict'));
    await t.pump();
    await t.pumpWidget(const SizedBox());
    await fake.dispose();
    await fake.connect();
    await pumpShell(t, fake);
    await goTo(t, 'Strictness');
    await t.pump(const Duration(seconds: 1));
    final g = t.widget<RadioGroup<Mode>>(find.byType(RadioGroup<Mode>));
    expect(g.groupValue, Mode.strict);
  });

  testWidgets('status badge shows when permissions are missing', (t) async {
    final f = FakeGuard(granted: const {}, autoGrant: false, statsPeriod: null);
    await f.connect();
    await pumpShell(t, f);
    expect(find.byType(Badge), findsOneWidget);
    expect(f.current.missing, isNotEmpty);
  });

  for (final label in labels) {
    testWidgets('a11y: $label (labels, tap targets, 200% text, dark)', (
      t,
    ) async {
      final h = t.ensureSemantics();
      await pumpShell(t, fake);
      await goTo(t, label);
      await t.pump();
      await expectLater(t, meetsGuideline(labeledTapTargetGuideline));
      await expectLater(t, meetsGuideline(androidTapTargetGuideline));
      await pumpShell(t, fake, scale: 2.0);
      await goTo(t, label);
      await t.pump();
      expect(t.takeException(), isNull);
      await pumpShell(t, fake, brightness: Brightness.dark);
      await goTo(t, label);
      await t.pump();
      expect(t.takeException(), isNull);
      h.dispose();
    });
  }
}
