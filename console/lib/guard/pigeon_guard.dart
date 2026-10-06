import 'dart:async';
import 'dart:io';

import 'package:flutter/services.dart';

import 'generated/guard_api.g.dart';
import 'guard_client.dart';
import 'pack_files.dart';

T _enum<T extends Enum>(List<T> values, String name, T fallback) {
  for (final v in values) {
    if (v.name == name) return v;
  }
  return fallback;
}

FileRef _ref(FileRefMsg m) => FileRef(m.path, m.sha256);
FileRefMsg _msg(FileRef r) => FileRefMsg(path: r.path, sha256: r.sha256);

ConceptView _concept(ConceptMsg m) => ConceptView(
  conceptId: m.conceptId,
  displayName: m.displayName,
  enabled: m.enabled,
  looksLike: m.looksLike,
  butNot: m.butNot,
  coverStyle: _enum(CoverStyle.values, m.coverStyle, CoverStyle.blur),
  examplePhotos: m.examplePhotos.map(_ref).toList(),
);

GuardState _state(StateMsg m) => GuardState(
  connection: Connection.connected,
  protocolVersion: m.protocolVersion,
  running: m.running,
  mode: _enum(Mode.values, m.mode, Mode.balanced),
  captureState: _enum(
    CaptureState.values,
    m.captureState,
    CaptureState.stopped,
  ),
  permissions: {for (final p in Perm.values) p: m.permissions[p.name] ?? false},
  skipList: m.skipList,
  concepts: m.concepts.map(_concept).toList(),
  activePackSha256: m.activePackSha256,
);

/// GuardClient over the Pigeon bridge to the Kotlin host in console/android.
class PigeonGuard implements GuardClient {
  PigeonGuard({
    GuardHostApi? api,
    Stream<StateMsg> Function()? stateStream,
    Stream<StatsMsg> Function()? statsStream,
    this._packDir,
  }) : _api = api ?? GuardHostApi(),
       _stateStream = stateStream ?? (() => streamState()),
       _statsStream = statsStream ?? (() => streamStats());

  final GuardHostApi _api;
  final Stream<StateMsg> Function() _stateStream;
  final Stream<StatsMsg> Function() _statsStream;
  final Directory? _packDir;

  GuardState _current = const GuardState();
  final _states = StreamController<GuardState>.broadcast();
  final _stats = StreamController<StatsTick>.broadcast();
  StreamSubscription<StateMsg>? _stateSub;
  StreamSubscription<StatsMsg>? _statsSub;

  void _set(GuardState s) {
    _current = s;
    if (!_states.isClosed) _states.add(s);
  }

  @override
  Future<GuardState> connect() async {
    HelloMsg hello;
    try {
      hello = await _api.hello();
    } on PlatformException {
      _set(_current.copyWith(connection: Connection.unavailable));
      rethrow;
    }
    if (hello.protocolVersion != kGuardProtocolVersion) {
      _set(
        _current.copyWith(
          connection: Connection.incompatible,
          protocolVersion: hello.protocolVersion,
        ),
      );
      throw GuardIncompatible(hello.protocolVersion);
    }
    _set(_state(await _api.getState()));
    await _stateSub?.cancel();
    await _statsSub?.cancel();
    _stateSub = _stateStream().listen((m) => _set(_state(m)), onError: (_) {});
    _statsSub = _statsStream().listen(
      (m) => _stats.add(
        StatsTick(
          tMs: m.tMs,
          looksPerSecond: m.looksPerSecond,
          aiMsLastLook: m.aiMsLastLook,
          batteryImpactPctPerHour: m.batteryImpactPctPerHour,
          activeCovers: m.activeCovers,
        ),
      ),
      onError: (_) {},
    );
    return _current;
  }

  @override
  GuardState get current => _current;
  @override
  Stream<GuardState> get states => _states.stream;
  @override
  Stream<StatsTick> get stats => _stats.stream;

  Future<void> _refresh() async => _set(_state(await _api.getState()));

  @override
  Future<void> start() async {
    await _api.start();
    await _refresh();
  }

  @override
  Future<void> stop() async {
    await _api.stop();
    await _refresh();
  }

  @override
  Future<void> setMode(Mode m) async {
    await _api.setMode(m.name);
    await _refresh();
  }

  @override
  Future<void> setSkipList(List<String> packages) async {
    await _api.setSkipList(packages);
    await _refresh();
  }

  @override
  Future<List<InstalledApp>> installedApps() async => [
    for (final a in await _api.installedApps())
      InstalledApp(a.packageName, a.label),
  ];

  @override
  Future<WordPreview> previewWord(String text) async =>
      WordPreview(word: text.trim());

  @override
  Future<ConceptView> compileConcept(
    String text,
    List<FileRef> photos, {
    List<String> alsoHide = const [],
  }) async =>
      _concept(await _api.compilePack(text, photos.map(_msg).toList()))
          .copyWith(alsoHide: alsoHide);

  PackResult _result(String s) => switch (s) {
    'accepted' => PackResult.accepted,
    'rejectedChecksum' => PackResult.rejectedChecksum,
    _ => PackResult.rejectedInvalid,
  };

  @override
  Future<PackResult> applyConcepts(List<ConceptView> concepts) async {
    final dir = _packDir ?? await Directory.systemTemp.createTemp('veil_packs');
    return setConceptPack(await writePack(concepts, dir));
  }

  @override
  Future<PackResult> setConceptPack(FileRef pack) async {
    final r = _result(await _api.setConceptPack(_msg(pack)));
    await _refresh();
    return r;
  }

  @override
  Future<void> submitFeedback(String coverId, FeedbackKind kind) =>
      _api.submitFeedback(coverId, kind.name);

  @override
  Future<List<RecentCover>> recentCovers({int limit = 20}) async => [
    for (final c in await _api.recentCovers(limit))
      RecentCover(
        coverId: c.coverId,
        conceptId: c.conceptId,
        thumbnailPath: c.thumbnailPath,
        tMs: c.tMs,
        mark: c.mark == null
            ? null
            : _enum(FeedbackKind.values, c.mark!, FeedbackKind.correct),
      ),
  ];

  @override
  Future<void> requestPermission(Perm p) async {
    await _api.requestPermission(p.name);
    await _refresh();
  }

  @override
  Future<void> dispose() async {
    await _stateSub?.cancel();
    await _statsSub?.cancel();
    await _states.close();
    await _stats.close();
  }
}
