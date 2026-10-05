import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:veil_console/guard/generated/guard_api.g.dart';
import 'package:veil_console/guard/guard_client.dart';
import 'package:veil_console/guard/pigeon_guard.dart';

class _Messenger implements BinaryMessenger {
  _Messenger(this.version);
  final int version;
  @override
  Future<ByteData?>? send(String channel, ByteData? message) async {
    const codec = GuardHostApi.pigeonChannelCodec;
    if (channel.endsWith('GuardHostApi.hello')) {
      return codec.encodeMessage(<Object?>[
        HelloMsg(protocolVersion: version, contractVersion: '1.0'),
      ]);
    }
    if (channel.endsWith('GuardHostApi.getState')) {
      return codec.encodeMessage(<Object?>[
        StateMsg(
          protocolVersion: version,
          running: false,
          mode: 'balanced',
          captureState: 'stopped',
          permissions: {'disclosure': true},
          skipList: [],
          concepts: [],
        ),
      ]);
    }
    return codec.encodeMessage(<Object?>[null]);
  }

  @override
  Future<void> handlePlatformMessage(
    String channel,
    ByteData? data,
    PlatformMessageResponseCallback? callback,
  ) async {}
  @override
  void setMessageHandler(String channel, MessageHandler? handler) {}
}

PigeonGuard _guard(int v) => PigeonGuard(
  api: GuardHostApi(binaryMessenger: _Messenger(v)),
  stateStream: () => const Stream<StateMsg>.empty(),
  statsStream: () => const Stream<StatsMsg>.empty(),
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('hello with matching version connects', () async {
    final s = await _guard(kGuardProtocolVersion).connect();
    expect(s.connection, Connection.connected);
    expect(s.permissions[Perm.disclosure], isTrue);
  });
  test('hello with other version is incompatible', () async {
    final g = _guard(7);
    await expectLater(g.connect(), throwsA(isA<GuardIncompatible>()));
    expect(g.current.connection, Connection.incompatible);
  });
}
