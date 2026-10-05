import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:veil_console/guard/fake_guard.dart';
import 'package:veil_console/guard/guard_client.dart';
import 'package:veil_console/guard/pack_files.dart';

void main() {
  test('commands round-trip and appear in calls and states', () async {
    final g = FakeGuard(statsPeriod: null);
    final seen = <GuardState>[];
    g.states.listen(seen.add);
    await g.connect();
    await g.start();
    await g.setMode(Mode.strict);
    await g.setSkipList(['com.example.bank']);
    await g.requestPermission(Perm.accessibility);
    await g.submitFeedback('cover-1', FeedbackKind.notThis);
    expect((await g.installedApps()).length, 4);
    final covers = await g.recentCovers();
    expect(covers.length, 3);
    expect(covers.first.mark, FeedbackKind.notThis);
    final c = await g.compileConcept('spiders', const []);
    expect(c.looksLike, isNotEmpty);
    expect(await g.applyConcepts([c]), PackResult.accepted);
    await Future<void>.delayed(Duration.zero);
    expect(g.current.running, isTrue);
    expect(g.current.mode, Mode.strict);
    expect(g.current.skipList, ['com.example.bank']);
    expect(g.current.permissions[Perm.accessibility], isTrue);
    expect(g.current.concepts.single.conceptId, 'spiders');
    expect(g.current.activePackSha256, isNotNull);
    expect(seen, isNotEmpty);
    expect(
      g.calls,
      containsAllInOrder([
        'connect',
        'start',
        'setMode',
        'setSkipList',
        'requestPermission',
      ]),
    );
    await g.dispose();
  });

  test('version mismatch throws GuardIncompatible', () async {
    final g = FakeGuard(protocolVersion: 99, statsPeriod: null);
    await expectLater(g.connect(), throwsA(isA<GuardIncompatible>()));
    expect(g.current.connection, Connection.incompatible);
  });

  test('corrupt pack is rejected and previous pack kept', () async {
    final g = FakeGuard(statsPeriod: null);
    await g.connect();
    final c = await g.compileConcept('x', const []);
    await g.applyConcepts([c]);
    final good = g.current.activePackSha256;
    final dir = await Directory.systemTemp.createTemp('veil_t');
    final ref = await writePack([c.copyWith(displayName: 'y')], dir);
    await File(ref.path).writeAsString('tampered');
    expect(await g.setConceptPack(ref), PackResult.rejectedChecksum);
    expect(g.current.activePackSha256, good);
  });

  test('dispose + reconnect keeps state', () async {
    final g = FakeGuard(statsPeriod: null);
    await g.connect();
    await g.start();
    await g.setMode(Mode.light);
    await g.dispose();
    final s = await g.connect();
    expect(s.running, isTrue);
    expect(s.mode, Mode.light);
    await g.dispose();
  });
}
