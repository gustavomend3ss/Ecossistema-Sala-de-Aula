import 'package:flutter/material.dart';

import '../../estado_app.dart';
import '../core/tema.dart';
import 'login_view_model.dart';

class LoginView extends StatefulWidget {
  const LoginView({super.key, required this.estado});
  final EstadoApp estado;

  @override
  State<LoginView> createState() => _LoginViewState();
}

class _LoginViewState extends State<LoginView> {
  late final LoginViewModel _vm = LoginViewModel(widget.estado);
  final _form = GlobalKey<FormState>();
  final _login = TextEditingController();
  final _senha = TextEditingController();
  bool _ocultar = true;

  @override
  void dispose() {
    _vm.dispose();
    _login.dispose();
    _senha.dispose();
    super.dispose();
  }

  void _enviar() {
    if (_form.currentState?.validate() ?? false) {
      _vm.entrar(_login.text, _senha.text);
    }
  }

  void _preencher(String login) {
    _login.text = login;
    _senha.text = 'demo123';
  }

  @override
  Widget build(BuildContext context) {
    final largo = MediaQuery.sizeOf(context).width >= 900;
    final formulario = _formulario();
    return Scaffold(
      backgroundColor: largo ? Cores.lateral : Cores.fundo,
      body: largo
          ? Row(children: [
              Expanded(child: _Apresentacao()),
              Container(
                width: 480,
                color: Cores.fundo,
                child: Center(child: SingleChildScrollView(padding: const EdgeInsets.all(40), child: formulario)),
              ),
            ])
          : SafeArea(
              child: Center(
                child: SingleChildScrollView(padding: const EdgeInsets.all(24), child: formulario),
              ),
            ),
    );
  }

  Widget _formulario() {
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 400),
      child: ListenableBuilder(
        listenable: _vm,
        builder: (context, _) => Form(
          key: _form,
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Text('FAINOR',
                style: TextStyle(fontSize: 30, fontWeight: FontWeight.w900, color: Cores.vermelho)),
            const Text('Gestão Acadêmica', style: TextStyle(color: Cores.textoSuave)),
            const SizedBox(height: 32),
            const Text('Entrar', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            const Text('Use as credenciais do seu perfil.', style: TextStyle(color: Cores.textoSuave)),
            const SizedBox(height: 24),
            TextFormField(
              controller: _login,
              decoration: const InputDecoration(labelText: 'Usuário', prefixIcon: Icon(Icons.person_outline)),
              validator: _vm.validarLogin,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.username],
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _senha,
              obscureText: _ocultar,
              decoration: InputDecoration(
                labelText: 'Senha',
                prefixIcon: const Icon(Icons.lock_outline),
                suffixIcon: IconButton(
                  tooltip: _ocultar ? 'Mostrar senha' : 'Ocultar senha',
                  icon: Icon(_ocultar ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                  onPressed: () => setState(() => _ocultar = !_ocultar),
                ),
              ),
              validator: _vm.validarSenha,
              onFieldSubmitted: (_) => _enviar(),
              autofillHints: const [AutofillHints.password],
            ),
            if (_vm.erro != null) ...[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                    color: Cores.vermelhoClaro, borderRadius: BorderRadius.circular(10)),
                child: Row(children: [
                  const Icon(Icons.error_outline, color: Cores.vermelho, size: 20),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_vm.erro!, style: const TextStyle(color: Cores.vermelho))),
                ]),
              ),
            ],
            const SizedBox(height: 22),
            FilledButton(
              onPressed: _vm.carregando ? null : _enviar,
              child: _vm.carregando
                  ? const SizedBox(
                      height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Entrar'),
            ),
            const SizedBox(height: 28),
            const Divider(),
            const SizedBox(height: 12),
            const Text('Acesso de demonstração (dados fictícios)',
                style: TextStyle(color: Cores.textoSuave, fontSize: 12.5)),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              ActionChip(label: const Text('Professor'), avatar: const Icon(Icons.school_outlined, size: 18),
                  onPressed: () => _preencher('prof.gabriel')),
              ActionChip(label: const Text('Aluna A01'), avatar: const Icon(Icons.person_outline, size: 18),
                  onPressed: () => _preencher('ana.lima')),
              ActionChip(label: const Text('Aluna A03'), avatar: const Icon(Icons.person_outline, size: 18),
                  onPressed: () => _preencher('carla.dias')),
            ]),
          ]),
        ),
      ),
    );
  }
}

class _Apresentacao extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(56),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
        const Text('Ecossistema de\nGestão Acadêmica',
            style: TextStyle(color: Colors.white, fontSize: 44, fontWeight: FontWeight.w800, height: 1.1)),
        const SizedBox(height: 18),
        const Text(
          'Registros, assistente e revisão do professor no mesmo fluxo.\n'
          'Cada alerta mostra a regra, o dado e o critério usados.',
          style: TextStyle(color: Color(0xFFC9C9CF), fontSize: 17, height: 1.5),
        ),
        const SizedBox(height: 36),
        for (final (icone, texto) in const [
          (Icons.fact_check_outlined, 'Notas e frequência por turma, com histórico de correções'),
          (Icons.rule_outlined, 'Alertas explicados por regras R1 a R5'),
          (Icons.verified_user_outlined, 'O professor confere, revisa e decide'),
        ])
          Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: Row(children: [
              Icon(icone, color: Cores.vermelho),
              const SizedBox(width: 12),
              Text(texto, style: const TextStyle(color: Colors.white, fontSize: 15)),
            ]),
          ),
      ]),
    );
  }
}
