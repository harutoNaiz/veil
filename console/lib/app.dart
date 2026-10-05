import 'package:flutter/material.dart';

import 'guard/guard_client.dart';
import 'onboarding/onboarding_flow.dart';
import 'screens/home_shell.dart';
import 'theme.dart';

class VeilConsoleApp extends StatelessWidget {
  final GuardClient guard;
  final PhotoSource? photos;
  final Widget Function(GuardClient)? homeBuilder;
  const VeilConsoleApp({
    super.key,
    required this.guard,
    this.photos,
    this.homeBuilder,
  });

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Veil Console',
      theme: veilLightTheme,
      darkTheme: veilDarkTheme,
      themeMode: ThemeMode.system,
      home: RootGate(
        guard: guard,
        homeBuilder: homeBuilder ?? (g) => HomeShell(guard: g, photos: photos),
      ),
    );
  }
}

class RootGate extends StatefulWidget {
  final GuardClient guard;
  final Widget Function(GuardClient) homeBuilder;
  const RootGate({super.key, required this.guard, required this.homeBuilder});

  @override
  State<RootGate> createState() => _RootGateState();
}

class _RootGateState extends State<RootGate> {
  late Future<GuardState> _connect;
  bool _inOnboarding = false;

  @override
  void initState() {
    super.initState();
    _connect = _doConnect();
  }

  Future<GuardState> _doConnect() async {
    try {
      return await widget.guard.connect();
    } on GuardIncompatible {
      return widget.guard.current;
    } catch (_) {
      return const GuardState(connection: Connection.unavailable);
    }
  }

  Widget _message(String title, String body) => Scaffold(
    body: SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                title,
                style: Theme.of(context).textTheme.headlineSmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              Text(body, textAlign: TextAlign.center),
            ],
          ),
        ),
      ),
    ),
  );

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<GuardState>(
      future: _connect,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        return StreamBuilder<GuardState>(
          stream: widget.guard.states,
          initialData: snap.data,
          builder: (context, s) {
            final st = s.data ?? snap.data!;
            switch (st.connection) {
              case Connection.incompatible:
                return _message(
                  'Update Veil',
                  'This app and the Veil service are different versions. Update Veil to continue.',
                );
              case Connection.unavailable:
                return _message(
                  'Veil service not running',
                  'Veil could not reach its background service. Restart the phone or reinstall Veil.',
                );
              case Connection.connecting:
                return const Scaffold(
                  body: Center(child: CircularProgressIndicator()),
                );
              case Connection.connected:
                break;
            }
            if (!st.setupComplete) _inOnboarding = true;
            if (_inOnboarding) {
              return OnboardingFlow(
                guard: widget.guard,
                onDone: () => setState(() => _inOnboarding = false),
              );
            }
            return widget.homeBuilder(widget.guard);
          },
        );
      },
    );
  }
}
