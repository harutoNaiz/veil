import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'guard_client.dart';
import 'pack_files.dart';

class FakePhotoSource implements PhotoSource {
  final List<FileRef> _photos;
  int _i = 0;
  FakePhotoSource(List<FileRef> photos) : _photos = List.of(photos);
  @override
  Future<FileRef?> pick() async => _i < _photos.length ? _photos[_i++] : null;
}

class FakeGuard implements GuardClient {
  FakeGuard({
    this.protocolVersion = kGuardProtocolVersion,
    Set<Perm> granted = const {},
    this.autoGrant = true,
    this.statsPeriod = const Duration(seconds: 1),
  }) : _granted = {...granted};

  final int protocolVersion;
  final bool autoGrant;
  final Duration? statsPeriod;
  final Set<Perm> _granted;
  final List<String> calls = [];

  Mode _mode = Mode.balanced;
  bool _running = false;
  List<String> _skip = [];
  List<ConceptView> _concepts = [];
  String? _packSha;
  Connection _conn = Connection.connecting;
  GuardState? _last;
  bool _wasRunning = false;
  bool _crashed = false;

  StreamController<GuardState> _states =
      StreamController<GuardState>.broadcast();
  StreamController<StatsTick> _stats = StreamController<StatsTick>.broadcast();
  Timer? _timer;
  int _tick = 0;
  Directory? _dir;

  GuardState _build() => GuardState(
    connection: _conn,
    protocolVersion: protocolVersion,
    running: _running,
    mode: _mode,
    captureState: _running
        ? CaptureState.running
        : _crashed
        ? CaptureState.stopped
        : (_granted.contains(Perm.screenCapture)
              ? CaptureState.stopped
              : CaptureState.awaitingPermission),
    permissions: {for (final p in Perm.values) p: _granted.contains(p)},
    skipList: List.unmodifiable(_skip),
    concepts: List.unmodifiable(_concepts),
    activePackSha256: _packSha,
  );

  void _emit() {
    _last = _build();
    if (!_states.isClosed) _states.add(_last!);
  }

  @override
  Future<GuardState> connect() async {
    calls.add('connect');
    if (_states.isClosed) _states = StreamController<GuardState>.broadcast();
    if (_stats.isClosed) _stats = StreamController<StatsTick>.broadcast();
    if (protocolVersion != kGuardProtocolVersion) {
      _conn = Connection.incompatible;
      _emit();
      throw GuardIncompatible(protocolVersion);
    }
    _conn = Connection.connected;
    if (_crashed) {
      _crashed = false;
      _running = _wasRunning;
    }
    _emit();
    final p = statsPeriod;
    _timer?.cancel();
    if (p != null) {
      _timer = Timer.periodic(p, (_) {
        _tick++;
        emitStats(
          StatsTick(
            tMs: _tick * p.inMilliseconds,
            looksPerSecond: _running ? 2 : 0,
            aiMsLastLook: _running ? 40 : 0,
            batteryImpactPctPerHour: _running ? 1.5 : 0,
          ),
        );
      });
    }
    return _last!;
  }

  void emitStats(StatsTick t) {
    if (!_stats.isClosed) _stats.add(t);
  }

  /// Test hook: the Guard process dies. Next connect() restores it.
  void simulateCrash() {
    _wasRunning = _running;
    _running = false;
    _crashed = true;
    _conn = Connection.unavailable;
    _emit();
  }

  /// Test hook: screen lock drops the capture grant.
  void simulateLock() {
    _running = false;
    _granted.remove(Perm.screenCapture);
    _emit();
  }

  void grant(Perm p) {
    _granted.add(p);
    _emit();
  }

  void revoke(Perm p) {
    _granted.remove(p);
    _emit();
  }

  @override
  GuardState get current => _last ?? _build();
  @override
  Stream<GuardState> get states => _states.stream;
  @override
  Stream<StatsTick> get stats => _stats.stream;

  @override
  Future<void> start() async {
    calls.add('start');
    _running = true;
    _emit();
  }

  @override
  Future<void> stop() async {
    calls.add('stop');
    _running = false;
    _emit();
  }

  @override
  Future<void> setMode(Mode m) async {
    calls.add('setMode');
    _mode = m;
    _emit();
  }

  @override
  Future<void> setSkipList(List<String> packages) async {
    calls.add('setSkipList');
    _skip = List.of(packages);
    _emit();
  }

  @override
  Future<List<InstalledApp>> installedApps() async {
    calls.add('installedApps');
    return const [
      InstalledApp('com.example.chat', 'Chat'),
      InstalledApp('com.example.video', 'Video'),
      InstalledApp('com.example.bank', 'Bank'),
      InstalledApp('com.example.maps', 'Maps'),
    ];
  }

  @override
  Future<ConceptView> compileConcept(String text, List<FileRef> photos) async {
    calls.add('compileConcept');
    final t = text.trim();
    final id = t
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
        .replaceAll(RegExp(r'^-+|-+$'), '');
    return ConceptView(
      conceptId: id.isEmpty ? 'concept' : id,
      displayName: t.isEmpty ? 'Concept' : t,
      looksLike: ['$t in photos', '$t in videos', 'drawings of $t'],
      butNot: ['toys that resemble $t', 'logos mentioning $t'],
      examplePhotos: photos,
    );
  }

  @override
  Future<PackResult> applyConcepts(List<ConceptView> concepts) async {
    calls.add('applyConcepts');
    _dir ??= await Directory.systemTemp.createTemp('veil_fake_packs');
    final ref = await writePack(concepts, _dir!);
    final r = await _setPack(ref);
    if (r == PackResult.accepted) {
      _concepts = List.of(concepts);
      _emit();
    }
    return r;
  }

  @override
  Future<PackResult> setConceptPack(FileRef pack) async {
    calls.add('setConceptPack');
    return _setPack(pack);
  }

  Future<PackResult> _setPack(FileRef pack) async {
    if (!await verifyFile(pack)) return PackResult.rejectedChecksum;
    try {
      final j = jsonDecode(await File(pack.path).readAsString());
      if (j is! Map ||
          j['contractVersion'] != '1.0' ||
          j['concepts'] is! List) {
        return PackResult.rejectedInvalid;
      }
    } catch (_) {
      return PackResult.rejectedInvalid;
    }
    _packSha = pack.sha256;
    _emit();
    return PackResult.accepted;
  }

  final Map<String, FeedbackKind> _marks = {};

  @override
  Future<void> submitFeedback(String coverId, FeedbackKind kind) async {
    calls.add('submitFeedback');
    _marks[coverId] = kind;
  }

  @override
  Future<List<RecentCover>> recentCovers({int limit = 20}) async {
    calls.add('recentCovers');
    final all = [
      for (var i = 1; i <= 3; i++)
        RecentCover(
          coverId: 'cover-$i',
          conceptId: 'concept-$i',
          thumbnailPath: '',
          tMs: i * 1000,
          mark: _marks['cover-$i'],
        ),
    ];
    return all.take(limit).toList();
  }

  @override
  Future<void> requestPermission(Perm p) async {
    calls.add('requestPermission');
    if (autoGrant) {
      _granted.add(p);
      _emit();
    }
  }

  @override
  Future<void> dispose() async {
    calls.add('dispose');
    _timer?.cancel();
    _timer = null;
    await _states.close();
    await _stats.close();
  }
}
