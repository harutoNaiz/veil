import 'package:flutter/material.dart';

import '../guard/guard_client.dart';

class StrictnessScreen extends StatefulWidget {
  const StrictnessScreen({super.key, required this.guard});
  final GuardClient guard;

  @override
  State<StrictnessScreen> createState() => _StrictnessScreenState();
}

class _StrictnessScreenState extends State<StrictnessScreen> {
  static const _lines = {
    Mode.light:
        'Covers slowest and uses the least battery. May miss quick scrolls.',
    Mode.balanced:
        'A middle path: covers fast enough with moderate battery use.',
    Mode.strict: 'Covers fastest and uses the most battery. More false covers.',
  };
  static const _names = {
    Mode.light: 'Light',
    Mode.balanced: 'Balanced',
    Mode.strict: 'Strict',
  };

  @override
  Widget build(BuildContext context) {
    final guard = widget.guard;
    return StreamBuilder<GuardState>(
      stream: guard.states,
      initialData: guard.current,
      builder: (context, _) {
        return RadioGroup<Mode>(
          groupValue: guard.current.mode,
          onChanged: (m) async {
            if (m == null) return;
            await guard.setMode(m);
            if (mounted) setState(() {});
          },
          child: ListView(
            children: [
              for (final m in Mode.values)
                RadioListTile<Mode>(
                  value: m,
                  title: Text(_names[m]!),
                  subtitle: Text(_lines[m]!),
                ),
            ],
          ),
        );
      },
    );
  }
}
