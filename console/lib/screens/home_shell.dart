import 'package:flutter/material.dart';

import '../guard/guard_client.dart';
import '../status/status_screen.dart';
import 'concept_studio_screen.dart';
import 'live_stats_screen.dart';
import 'recent_covers_screen.dart';
import 'skip_list_screen.dart';
import 'strictness_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key, required this.guard, this.photos});
  final GuardClient guard;
  final PhotoSource? photos;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  Widget _body() {
    switch (_index) {
      case 0:
        return ConceptStudioScreen(guard: widget.guard, photos: widget.photos);
      case 1:
        return StrictnessScreen(guard: widget.guard);
      case 2:
        return SkipListScreen(guard: widget.guard);
      case 3:
        return LiveStatsScreen(guard: widget.guard);
      default:
        return RecentCoversScreen(guard: widget.guard);
    }
  }

  @override
  Widget build(BuildContext context) {
    final g = widget.guard;
    return StreamBuilder<GuardState>(
      stream: g.states,
      initialData: g.current,
      builder: (context, _) {
        final s = g.current;
        return Scaffold(
          appBar: AppBar(
            title: const Text('Veil'),
            actions: [
              Semantics(
                label: 'Start or stop covering',
                child: Switch(
                  value: s.running,
                  onChanged: (v) => v ? g.start() : g.stop(),
                ),
              ),
              IconButton(
                tooltip: 'Status',
                icon: Badge(
                  isLabelVisible: s.missing.isNotEmpty,
                  child: const Icon(Icons.shield_outlined),
                ),
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => Scaffold(
                      appBar: AppBar(title: const Text('Status')),
                      body: StatusScreen(guard: g),
                    ),
                  ),
                ),
              ),
            ],
          ),
          body: _body(),
          bottomNavigationBar: NavigationBar(
            selectedIndex: _index,
            onDestinationSelected: (i) => setState(() => _index = i),
            destinations: const [
              NavigationDestination(icon: Icon(Icons.block), label: 'Concepts'),
              NavigationDestination(
                icon: Icon(Icons.tune),
                label: 'Strictness',
              ),
              NavigationDestination(icon: Icon(Icons.apps), label: 'Skip list'),
              NavigationDestination(
                icon: Icon(Icons.show_chart),
                label: 'Stats',
              ),
              NavigationDestination(icon: Icon(Icons.history), label: 'Recent'),
            ],
          ),
        );
      },
    );
  }
}
