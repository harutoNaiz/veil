const int kGuardProtocolVersion = 1;

enum Mode { light, balanced, strict }

enum Perm {
  disclosure,
  accessibility,
  restrictedSettings,
  screenCapture,
  notifications,
}

enum CaptureState { running, paused, stopped, awaitingPermission }

enum Connection { connecting, connected, incompatible, unavailable }

enum FeedbackKind { correct, notThis, missed }

enum CoverStyle { solid, blur, mosaic }

enum PackResult { accepted, rejectedChecksum, rejectedInvalid }

class FileRef {
  final String path;
  final String sha256;
  const FileRef(this.path, this.sha256);
}

class ConceptView {
  final String conceptId, displayName;
  final bool enabled;
  final List<String> looksLike, butNot;
  final CoverStyle coverStyle;
  final List<FileRef> examplePhotos;
  const ConceptView({
    required this.conceptId,
    required this.displayName,
    this.enabled = true,
    this.looksLike = const [],
    this.butNot = const [],
    this.coverStyle = CoverStyle.blur,
    this.examplePhotos = const [],
  });
  ConceptView copyWith({
    String? conceptId,
    String? displayName,
    bool? enabled,
    List<String>? looksLike,
    List<String>? butNot,
    CoverStyle? coverStyle,
    List<FileRef>? examplePhotos,
  }) => ConceptView(
    conceptId: conceptId ?? this.conceptId,
    displayName: displayName ?? this.displayName,
    enabled: enabled ?? this.enabled,
    looksLike: looksLike ?? this.looksLike,
    butNot: butNot ?? this.butNot,
    coverStyle: coverStyle ?? this.coverStyle,
    examplePhotos: examplePhotos ?? this.examplePhotos,
  );
}

class GuardState {
  final Connection connection;
  final int protocolVersion;
  final bool running;
  final Mode mode;
  final CaptureState captureState;
  final Map<Perm, bool> permissions;
  final List<String> skipList;
  final List<ConceptView> concepts;
  final String? activePackSha256;
  const GuardState({
    this.connection = Connection.connecting,
    this.protocolVersion = 0,
    this.running = false,
    this.mode = Mode.balanced,
    this.captureState = CaptureState.stopped,
    this.permissions = const {},
    this.skipList = const [],
    this.concepts = const [],
    this.activePackSha256,
  });
  List<Perm> get missing =>
      Perm.values.where((p) => permissions[p] != true).toList();
  bool get setupComplete => missing.isEmpty;
  GuardState copyWith({
    Connection? connection,
    int? protocolVersion,
    bool? running,
    Mode? mode,
    CaptureState? captureState,
    Map<Perm, bool>? permissions,
    List<String>? skipList,
    List<ConceptView>? concepts,
    String? activePackSha256,
  }) => GuardState(
    connection: connection ?? this.connection,
    protocolVersion: protocolVersion ?? this.protocolVersion,
    running: running ?? this.running,
    mode: mode ?? this.mode,
    captureState: captureState ?? this.captureState,
    permissions: permissions ?? this.permissions,
    skipList: skipList ?? this.skipList,
    concepts: concepts ?? this.concepts,
    activePackSha256: activePackSha256 ?? this.activePackSha256,
  );
}

class StatsTick {
  final int tMs;
  final double looksPerSecond, aiMsLastLook, batteryImpactPctPerHour;
  final int activeCovers;
  const StatsTick({
    required this.tMs,
    this.looksPerSecond = 0,
    this.aiMsLastLook = 0,
    this.batteryImpactPctPerHour = 0,
    this.activeCovers = 0,
  });
}

class RecentCover {
  final String coverId, conceptId, thumbnailPath;
  final int tMs;
  final FeedbackKind? mark;
  const RecentCover({
    required this.coverId,
    required this.conceptId,
    required this.thumbnailPath,
    required this.tMs,
    this.mark,
  });
}

class InstalledApp {
  final String package, label;
  const InstalledApp(this.package, this.label);
}

class GuardIncompatible implements Exception {
  final int guardVersion;
  const GuardIncompatible(this.guardVersion);
  @override
  String toString() => 'GuardIncompatible(guardVersion: $guardVersion)';
}

abstract class PhotoSource {
  Future<FileRef?> pick();
}

abstract class GuardClient {
  /// hello -> version check; mismatch throws GuardIncompatible and state.connection=incompatible
  Future<GuardState> connect();

  /// last known state, read from the Guard (never cached on disk by the app)
  GuardState get current;

  /// engine state + permissions; emits on every change
  Stream<GuardState> get states;

  /// ~1 per second
  Stream<StatsTick> get stats;

  Future<void> start();
  Future<void> stop();
  Future<void> setMode(Mode m);
  Future<void> setSkipList(List<String> packages);
  Future<List<InstalledApp>> installedApps();

  /// draft with looksLike/butNot
  Future<ConceptView> compileConcept(String text, List<FileRef> photos);

  /// writes pack file + setConceptPack
  Future<PackResult> applyConcepts(List<ConceptView> concepts);

  /// checksum/schema check; on reject the old pack stays
  Future<PackResult> setConceptPack(FileRef pack);

  Future<void> submitFeedback(String coverId, FeedbackKind kind);
  Future<List<RecentCover>> recentCovers({int limit = 20});

  /// opens the system screen; disclosure = consent accepted
  Future<void> requestPermission(Perm p);
  Future<void> dispose();
}
