import 'package:flutter_test/flutter_test.dart';
import 'package:veil_console/app.dart';
import 'package:veil_console/guard/fake_guard.dart';

void main() {
  testWidgets('app boots into onboarding', (tester) async {
    await tester.pumpWidget(
      VeilConsoleApp(guard: FakeGuard(statsPeriod: null)),
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('Set up Veil'), findsOneWidget);
  });
}
