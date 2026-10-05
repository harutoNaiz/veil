import 'package:flutter/material.dart';

import '../guard/guard_client.dart';
import '../onboarding/perm_info.dart';

class StatusScreen extends StatelessWidget {
  final GuardClient guard;
  const StatusScreen({super.key, required this.guard});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<GuardState>(
      stream: guard.states,
      initialData: guard.current,
      builder: (context, snap) {
        final st = snap.data ?? guard.current;
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              st.running ? 'Veil is running' : 'Veil is not running',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 4),
            Text('Capture: ${st.captureState.name}'),
            const SizedBox(height: 16),
            for (final p in Perm.values)
              _row(context, p, st.permissions[p] == true),
          ],
        );
      },
    );
  }

  Widget _row(BuildContext context, Perm p, bool ok) {
    final info = permInfo[p]!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              ok ? Icons.check_circle : Icons.error_outline,
              semanticLabel: ok ? 'On' : 'Missing',
              color: ok ? Colors.green : Theme.of(context).colorScheme.error,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    info.title,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  Text(ok ? 'On' : 'Missing: ${info.reason}'),
                ],
              ),
            ),
            if (!ok) ...[
              const SizedBox(width: 8),
              FilledButton.tonal(
                onPressed: () => guard.requestPermission(p),
                child: const Text('Fix'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
