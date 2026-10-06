import 'package:flutter_test/flutter_test.dart';
import 'package:veil_console/guard/guard_client.dart';
import 'package:veil_console/guard/pack_files.dart';

void main() {
  test('pack json carries alsoHide only when set', () {
    const plain = ConceptView(conceptId: 'a', displayName: 'A');
    expect(conceptToJson(plain).containsKey('alsoHide'), isFalse);
    final j = conceptToJson(plain.copyWith(alsoHide: ['x', 'y']));
    expect(j['alsoHide'], ['x', 'y']);
  });
}
