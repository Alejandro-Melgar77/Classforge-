import 'package:flutter_test/flutter_test.dart';
import 'package:classforge_mobile/main.dart';

void main() {
  testWidgets('ClassForge app smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const ClassForgeMobileApp());
    expect(find.byType(ClassForgeMobileApp), findsOneWidget);
  });
}
