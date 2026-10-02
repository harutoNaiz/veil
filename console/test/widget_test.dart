import 'package:flutter_test/flutter_test.dart';
import 'package:veil_console/main.dart';

void main() {
  testWidgets('shows the Veil Console title', (WidgetTester tester) async {
    await tester.pumpWidget(const VeilConsoleApp());

    expect(find.text('Veil Console'), findsOneWidget);
    expect(find.text('Hello from Phase 1.1'), findsOneWidget);
  });
}
