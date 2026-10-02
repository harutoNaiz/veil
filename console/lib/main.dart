import 'package:flutter/material.dart';

void main() {
  debugPrint('VEIL_CONSOLE_HELLO');
  runApp(const VeilConsoleApp());
}

class VeilConsoleApp extends StatelessWidget {
  const VeilConsoleApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      title: 'Veil Console',
      home: Scaffold(
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Veil Console',
                style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 12),
              Text('Hello from Phase 1.1'),
            ],
          ),
        ),
      ),
    );
  }
}
