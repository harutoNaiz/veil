import 'package:flutter/material.dart';

import '../guard/guard_client.dart';

class SkipListScreen extends StatefulWidget {
  const SkipListScreen({super.key, required this.guard});
  final GuardClient guard;

  @override
  State<SkipListScreen> createState() => _SkipListScreenState();
}

class _SkipListScreenState extends State<SkipListScreen> {
  late final Future<List<InstalledApp>> _apps = widget.guard.installedApps();
  late final Set<String> _skip = widget.guard.current.skipList.toSet();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<InstalledApp>>(
      future: _apps,
      builder: (context, snap) {
        final apps = snap.data;
        if (apps == null)
          return const Center(child: CircularProgressIndicator());
        return ListView(
          children: [
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                'Veil will not cover anything inside the checked apps.',
              ),
            ),
            for (final a in apps)
              CheckboxListTile(
                value: _skip.contains(a.package),
                title: Text(a.label),
                onChanged: (v) async {
                  setState(
                    () => v == true
                        ? _skip.add(a.package)
                        : _skip.remove(a.package),
                  );
                  await widget.guard.setSkipList(_skip.toList());
                },
              ),
          ],
        );
      },
    );
  }
}
