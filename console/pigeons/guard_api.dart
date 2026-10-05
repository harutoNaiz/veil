import 'package:pigeon/pigeon.dart';

@ConfigurePigeon(
  PigeonOptions(
    dartOut: 'lib/guard/generated/guard_api.g.dart',
    kotlinOut:
        'android/app/src/main/kotlin/com/veil/console/bridge/GuardApi.g.kt',
    kotlinOptions: KotlinOptions(package: 'com.veil.console.bridge'),
  ),
)
class HelloMsg {
  HelloMsg({required this.protocolVersion, required this.contractVersion});
  int protocolVersion;
  String contractVersion;
}

class FileRefMsg {
  FileRefMsg({required this.path, required this.sha256});
  String path;
  String sha256;
}

class ConceptMsg {
  ConceptMsg({
    required this.conceptId,
    required this.displayName,
    required this.enabled,
    required this.looksLike,
    required this.butNot,
    required this.coverStyle,
    required this.examplePhotos,
  });
  String conceptId;
  String displayName;
  bool enabled;
  List<String> looksLike;
  List<String> butNot;
  String coverStyle;
  List<FileRefMsg> examplePhotos;
}

class StateMsg {
  StateMsg({
    required this.protocolVersion,
    required this.running,
    required this.mode,
    required this.captureState,
    required this.permissions,
    required this.skipList,
    required this.concepts,
    this.activePackSha256,
  });
  int protocolVersion;
  bool running;
  String mode;
  String captureState;
  Map<String, bool> permissions;
  List<String> skipList;
  List<ConceptMsg> concepts;
  String? activePackSha256;
}

class StatsMsg {
  StatsMsg({
    required this.tMs,
    required this.looksPerSecond,
    required this.aiMsLastLook,
    required this.batteryImpactPctPerHour,
    required this.activeCovers,
  });
  int tMs;
  double looksPerSecond;
  double aiMsLastLook;
  double batteryImpactPctPerHour;
  int activeCovers;
}

class InstalledAppMsg {
  InstalledAppMsg({required this.package, required this.label});
  String package;
  String label;
}

class RecentCoverMsg {
  RecentCoverMsg({
    required this.coverId,
    required this.conceptId,
    required this.thumbnailPath,
    required this.tMs,
    this.mark,
  });
  String coverId;
  String conceptId;
  String thumbnailPath;
  int tMs;
  String? mark;
}

@HostApi()
abstract class GuardHostApi {
  @TaskQueue(type: TaskQueueType.serialBackgroundThread)
  HelloMsg hello();

  @TaskQueue(type: TaskQueueType.serialBackgroundThread)
  StateMsg getState();

  @TaskQueue(type: TaskQueueType.serialBackgroundThread)
  void start();

  @TaskQueue(type: TaskQueueType.serialBackgroundThread)
  void stop();

  @TaskQueue(type: TaskQueueType.serialBackgroundThread)
  void setMode(String mode);

  @TaskQueue(type: TaskQueueType.serialBackgroundThread)
  void setSkipList(List<String> packages);

  @TaskQueue(type: TaskQueueType.serialBackgroundThread)
  List<InstalledAppMsg> installedApps();

  @TaskQueue(type: TaskQueueType.serialBackgroundThread)
  ConceptMsg compilePack(String text, List<FileRefMsg> photos);

  @TaskQueue(type: TaskQueueType.serialBackgroundThread)
  String setConceptPack(FileRefMsg pack);

  @TaskQueue(type: TaskQueueType.serialBackgroundThread)
  void submitFeedback(String coverId, String kind);

  @TaskQueue(type: TaskQueueType.serialBackgroundThread)
  List<RecentCoverMsg> recentCovers(int limit);

  @TaskQueue(type: TaskQueueType.serialBackgroundThread)
  void requestPermission(String perm);
}

@EventChannelApi()
abstract class GuardEvents {
  StateMsg streamState();
  StatsMsg streamStats();
}
