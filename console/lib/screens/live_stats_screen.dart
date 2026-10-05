import 'package:flutter/material.dart';

import '../guard/guard_client.dart';

class LiveStatsScreen extends StatelessWidget {
  const LiveStatsScreen({super.key, required this.guard});
  final GuardClient guard;

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<StatsTick>(
      stream: guard.stats,
      builder: (context, snap) {
        final t = snap.data;
        String f(num? v, [int d = 1]) => v == null ? '—' : v.toStringAsFixed(d);
        return ListView(
          children: [
            ListTile(
              title: const Text('Looks per second'),
              trailing: Text(f(t?.looksPerSecond)),
            ),
            ListTile(
              title: const Text('Covers on screen'),
              trailing: Text(f(t?.activeCovers, 0)),
            ),
            ListTile(
              title: const Text('AI time (ms)'),
              trailing: Text(f(t?.aiMsLastLook)),
            ),
            ListTile(
              title: const Text('Battery impact (%/h)'),
              trailing: Text(f(t?.batteryImpactPctPerHour)),
            ),
          ],
        );
      },
    );
  }
}
