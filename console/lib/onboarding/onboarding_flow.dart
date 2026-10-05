import 'package:flutter/material.dart';

import '../guard/guard_client.dart';
import 'perm_info.dart';

/// Walks the user through every [Perm] in order. The current page is the first
/// missing permission, so it advances by itself when `states` shows it granted.
class OnboardingFlow extends StatelessWidget {
  final GuardClient guard;
  final VoidCallback? onDone;
  const OnboardingFlow({super.key, required this.guard, this.onDone});

  static const _intro = {
    Perm.disclosure:
        'Veil watches your screen on this phone and covers content you chose to avoid. '
        'Nothing leaves your phone: no screenshots, no uploads.',
    Perm.accessibility: 'Turn on "Veil" in Accessibility settings. This lets Veil draw a cover over the screen.',
    Perm.restrictedSettings:
        'If Android says "Restricted setting", open Settings, then Apps, then Veil, '
        'tap the three-dot menu and choose "Allow restricted settings".',
    Perm.screenCapture:
        'Choose "Entire screen" when Android asks. Android asks again after you lock the phone, '
        'because it ends screen sharing on lock.',
    Perm.notifications: 'Veil shows a "Resume Veil" notification so you can restart protection in one tap.',
  };

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<GuardState>(
      stream: guard.states,
      initialData: guard.current,
      builder: (context, snap) {
        final st = snap.data ?? guard.current;
        final missing = st.missing;
        final theme = Theme.of(context);
        final Widget body;
        final String step;
        if (missing.isEmpty) {
          step = 'Done';
          body = _page(
            theme,
            key: const ValueKey('done'),
            title: 'Veil is ready',
            text: 'All permissions are set. Veil can now protect your screen.',
            button: FilledButton(
              onPressed: onDone,
              child: const Text('Start using Veil'),
            ),
          );
        } else {
          final p = missing.first;
          final info = permInfo[p]!;
          step = 'Step ${Perm.values.indexOf(p) + 1} of ${Perm.values.length}';
          body = _page(
            theme,
            key: ValueKey(p),
            title: info.title,
            text: _intro[p]!,
            button: FilledButton(
              onPressed: () => guard.requestPermission(p),
              child: Text(info.action),
            ),
          );
        }
        return Scaffold(
          appBar: AppBar(title: Text('Set up Veil - $step')),
          body: SafeArea(child: body),
        );
      },
    );
  }

  Widget _page(
    ThemeData theme, {
    Key? key,
    required String title,
    required String text,
    required Widget button,
  }) {
    return SingleChildScrollView(
      key: key,
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(title, style: theme.textTheme.headlineSmall),
          const SizedBox(height: 16),
          Text(text, style: theme.textTheme.bodyLarge),
          const SizedBox(height: 32),
          button,
        ],
      ),
    );
  }
}
