import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';

import 'guard_client.dart';

Map<String, Object?> conceptToJson(ConceptView c) => {
  'contractVersion': '1.0',
  'conceptId': c.conceptId,
  'displayName': c.displayName,
  'layer': 2,
  'enabled': c.enabled,
  'looksLike': c.looksLike,
  'butNot': c.butNot,
  'coverStyle': c.coverStyle.name,
  'examplePhotos': [
    for (final p in c.examplePhotos) {'path': p.path, 'sha256': p.sha256},
  ],
  if (c.alsoHide.isNotEmpty) 'alsoHide': c.alsoHide,
};

/// Writes a concept-pack JSON (contractVersion "1.0") into [dir]; returns path + sha256.
Future<FileRef> writePack(List<ConceptView> concepts, Directory dir) async {
  await dir.create(recursive: true);
  final bytes = utf8.encode(
    jsonEncode({
      'contractVersion': '1.0',
      'packId': 'my-concepts',
      'name': 'My concepts',
      'version': '1.0.0',
      'concepts': [for (final c in concepts) conceptToJson(c)],
    }),
  );
  final hash = sha256.convert(bytes).toString();
  final file = File(
    '${dir.path}${Platform.pathSeparator}pack-${hash.substring(0, 12)}.json',
  );
  await file.writeAsBytes(bytes, flush: true);
  return FileRef(file.path, hash);
}

/// True when the file exists and its sha256 equals [ref].sha256.
Future<bool> verifyFile(FileRef ref) async {
  final f = File(ref.path);
  if (!await f.exists()) return false;
  return sha256.convert(await f.readAsBytes()).toString() == ref.sha256;
}
