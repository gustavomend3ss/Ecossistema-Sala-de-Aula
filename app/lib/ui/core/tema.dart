import 'package:flutter/material.dart';

class Cores {
  static const vermelho = Color(0xFFC8102E);
  static const vermelhoClaro = Color(0xFFFDE4E7);
  static const lateral = Color(0xFF141414);
  static const fundo = Color(0xFFF6F6F7);
  static const borda = Color(0xFFE3E3E6);
  static const texto = Color(0xFF1B1B1F);
  static const textoSuave = Color(0xFF63636B);
  static const ambar = Color(0xFF8A5A00);
  static const ambarClaro = Color(0xFFFFF1D6);
  static const verde = Color(0xFF1E6B3A);
  static const verdeClaro = Color(0xFFE3F3E8);
  static const azul = Color(0xFF1F4E8C);
  static const azulClaro = Color(0xFFE5EEFA);
  static const cinzaClaro = Color(0xFFEDEDEF);
}

ThemeData temaFainor() {
  final esquema = ColorScheme.fromSeed(
    seedColor: Cores.vermelho,
    primary: Cores.vermelho,
    surface: Colors.white,
  );
  return ThemeData(
    useMaterial3: true,
    fontFamily: 'Roboto',
    colorScheme: esquema,
    scaffoldBackgroundColor: Cores.fundo,
    dividerColor: Cores.borda,
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.white,
      foregroundColor: Cores.texto,
      elevation: 0,
      scrolledUnderElevation: 0,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: Cores.borda),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: Cores.vermelho,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: Cores.texto,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        side: const BorderSide(color: Cores.borda),
      ),
    ),
  );
}
