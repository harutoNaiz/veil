import 'package:flutter/material.dart';

ThemeData _build(Brightness b) => ThemeData(
  useMaterial3: true,
  colorScheme: ColorScheme.fromSeed(
    seedColor: const Color(0xFF3F51B5),
    brightness: b,
  ),
  materialTapTargetSize: MaterialTapTargetSize.padded,
);

final ThemeData veilLightTheme = _build(Brightness.light);
final ThemeData veilDarkTheme = _build(Brightness.dark);
