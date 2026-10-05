import 'dart:io';

import 'package:flutter/material.dart';

import '../guard/guard_client.dart';

class RecentCoversScreen extends StatefulWidget {
  const RecentCoversScreen({super.key, required this.guard});
  final GuardClient guard;

  @override
  State<RecentCoversScreen> createState() => _RecentCoversScreenState();
}

class _RecentCoversScreenState extends State<RecentCoversScreen> {
  late final Future<List<RecentCover>> _covers = widget.guard.recentCovers();
  final Map<String, FeedbackKind> _marks = {};

  Widget _btn(RecentCover c, FeedbackKind k, String label) {
    final selected = (_marks[c.coverId] ?? c.mark) == k;
    Future<void> onTap() async {
      setState(() => _marks[c.coverId] = k);
      await widget.guard.submitFeedback(c.coverId, k);
    }

    final child = Text(selected ? '$label ✓' : label);
    return selected
        ? FilledButton.tonal(onPressed: onTap, child: child)
        : OutlinedButton(onPressed: onTap, child: child);
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<RecentCover>>(
      future: _covers,
      builder: (context, snap) {
        final covers = snap.data;
        if (covers == null)
          return const Center(child: CircularProgressIndicator());
        if (covers.isEmpty) return const Center(child: Text('No covers yet.'));
        return ListView(
          children: [
            for (final c in covers)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        height: 96,
                        child: Image.file(
                          File(c.thumbnailPath),
                          fit: BoxFit.cover,
                          excludeFromSemantics: true,
                          errorBuilder: (context, error, stack) =>
                              const Icon(Icons.broken_image),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _btn(c, FeedbackKind.correct, 'Correct'),
                          _btn(c, FeedbackKind.notThis, 'Not this'),
                          _btn(c, FeedbackKind.missed, 'Missed one'),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}
