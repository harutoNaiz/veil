import 'package:flutter/material.dart';

import 'app.dart';
import 'guard/guard_factory.dart';

void main() {
  runApp(VeilConsoleApp(guard: createGuard()));
}
