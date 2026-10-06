import 'package:flutter/material.dart';

import '../guard/guard_client.dart';

class ConceptStudioScreen extends StatefulWidget {
  const ConceptStudioScreen({super.key, required this.guard, this.photos});
  final GuardClient guard;
  final PhotoSource? photos;

  @override
  State<ConceptStudioScreen> createState() => _ConceptStudioScreenState();
}

class _ConceptStudioScreenState extends State<ConceptStudioScreen> {
  final _text = TextEditingController();
  final List<FileRef> _photos = [];
  ConceptView? _draft;
  CoverStyle _style = CoverStyle.blur;
  WordPreview? _wp;
  final Set<String> _sel = {};

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  void _report(PackResult r) {
    if (r != PackResult.accepted && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Pack rejected; previous pack still active'),
        ),
      );
    }
  }

  Future<void> _addPhoto() async {
    final f = await widget.photos?.pick();
    if (f != null && mounted) setState(() => _photos.add(f));
  }

  Future<void> _onText(String v) async {
    final t = v.trim();
    if (t.isEmpty) {
      setState(() {
        _wp = null;
        _sel.clear();
      });
      return;
    }
    final p = await widget.guard.previewWord(t);
    if (mounted && _text.text.trim() == t) {
      setState(() {
        _wp = p;
        _sel.clear();
      });
    }
  }

  Future<void> _add() async {
    final text = _text.text.trim();
    if (text.isEmpty) return;
    final d = await widget.guard.compileConcept(
      text,
      List.of(_photos),
      alsoHide: _sel.toList(),
    );
    final r = await widget.guard.applyConcepts([
      ...widget.guard.current.concepts,
      d.copyWith(coverStyle: _style),
    ]);
    _report(r);
    if (mounted && r == PackResult.accepted) {
      setState(() {
        _draft = null;
        _wp = null;
        _sel.clear();
        _photos.clear();
        _text.clear();
      });
    }
  }

  Future<void> _generate() async {
    final text = _text.text.trim();
    if (text.isEmpty) return;
    final d = await widget.guard.compileConcept(text, List.of(_photos));
    if (mounted) setState(() => _draft = d);
  }

  Future<void> _save() async {
    final d = _draft;
    if (d == null) return;
    final all = [
      ...widget.guard.current.concepts,
      d.copyWith(coverStyle: _style),
    ];
    final r = await widget.guard.applyConcepts(all);
    _report(r);
    if (mounted && r == PackResult.accepted) {
      setState(() {
        _draft = null;
        _photos.clear();
        _text.clear();
      });
    }
  }

  Future<void> _toggle(ConceptView c, bool on) async {
    final all = [
      for (final x in widget.guard.current.concepts)
        x.conceptId == c.conceptId ? x.copyWith(enabled: on) : x,
    ];
    _report(await widget.guard.applyConcepts(all));
    if (mounted) setState(() {});
  }

  Widget _chips(String title, List<String> items) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(title, style: Theme.of(context).textTheme.titleSmall),
      Wrap(spacing: 8, children: [for (final i in items) Chip(label: Text(i))]),
    ],
  );

  @override
  Widget build(BuildContext context) {
    final d = _draft;
    return StreamBuilder<GuardState>(
      stream: widget.guard.states,
      initialData: widget.guard.current,
      builder: (context, _) {
        final concepts = widget.guard.current.concepts;
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextField(
              controller: _text,
              onChanged: _onText,
              decoration: const InputDecoration(
                labelText: 'What do you want hidden?',
              ),
            ),
            if (_wp != null && d == null) ...[
              const SizedBox(height: 8),
              Text('Also hide:', style: Theme.of(context).textTheme.titleSmall),
              Wrap(
                spacing: 8,
                children: [
                  for (final c in _wp!.alsoHide)
                    FilterChip(
                      label: Text(c),
                      selected: _sel.contains(c),
                      onSelected: (on) => setState(() {
                        on ? _sel.add(c) : _sel.remove(c);
                      }),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              SizedBox(
                height: 56,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: [
                    for (final p in _wp!.preview)
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: Chip(label: Text(p)),
                      ),
                  ],
                ),
              ),
              Text('Active in ${_wp!.elapsedMs} ms'),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton(onPressed: _add, child: const Text('Add')),
              ),
            ],
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton(
                  onPressed: widget.photos == null ? null : _addPhoto,
                  child: Text(
                    _photos.isEmpty
                        ? 'Add example photo'
                        : 'Add example photo (${_photos.length})',
                  ),
                ),
                FilledButton(
                  onPressed: _generate,
                  child: const Text('Preview'),
                ),
              ],
            ),
            if (d != null) ...[
              const SizedBox(height: 16),
              _chips('Looks like', d.looksLike),
              const SizedBox(height: 8),
              _chips('But not', d.butNot),
              const SizedBox(height: 8),
              SegmentedButton<CoverStyle>(
                segments: const [
                  ButtonSegment(value: CoverStyle.solid, label: Text('Solid')),
                  ButtonSegment(value: CoverStyle.blur, label: Text('Blur')),
                  ButtonSegment(
                    value: CoverStyle.mosaic,
                    label: Text('Mosaic'),
                  ),
                ],
                selected: {_style},
                onSelectionChanged: (s) => setState(() => _style = s.first),
              ),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton(
                  onPressed: _save,
                  child: const Text('Save'),
                ),
              ),
            ],
            const Divider(height: 32),
            if (concepts.isEmpty) const Text('No concepts yet.'),
            for (final c in concepts)
              SwitchListTile(
                title: Text(c.displayName),
                value: c.enabled,
                onChanged: (v) => _toggle(c, v),
              ),
          ],
        );
      },
    );
  }
}
