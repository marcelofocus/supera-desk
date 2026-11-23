# 🖥️ Supera-Desk — Fábrica Corporativa do Cliente Nativo de Suporte Remoto (Supera ERP)

Esta pasta da camada corporativa (`platform/supera-desk`) contém a fábrica automatizada de compilação do **Supera-Desk**: o cliente desktop nativo (Windows 10/11 x64 e macOS Apple Silicon) 100% **White-Label** do **Supera ERP / focuSolution**, derivado da engine upstream `RustDesk 1.3.8` (Rust + Flutter + Codec GPU por Hardware).

---

## 1. O que já vem pré-configurado dentro do binário

Ao abrir o **Supera-Desk** em qualquer máquina Windows ou Mac, o colaborador ou analista **não precisa configurar rede, servidor nem chave**:

| Parâmetro | Valor Compilado de Fábrica |
| :--- | :--- |
| **Nome do Produto / Serviço** | `Supera-Desk` (`C:\Program Files\Supera-Desk\Supera-Desk.exe` e `/Applications/Supera-Desk.app`) |
| **Bundle / Organização** | `br.com.focusolution.supera-desk` |
| **Servidor ID (`hbbs`)** | `superadesk.ipog.cloud` (TCP/UDP `21116`) |
| **Servidor Relay (`hbbr`)** | `superadesk.ipog.cloud` (TCP `21117`) |
| **Chave Pública (`Ed25519`)** | `MwoPxCW4rXbAXrMf0F9Mmo5NOqpYp1EVtTZAeJORUpo=` |
| **Modo UDP Direto + GPU** | `direct-server = Y`, `enable-hwcodec = Y`, `enable-abr = Y` |
| **Protocolos URI 1-Clique** | `supera-desk://` e `superadesk://` (com suporte nativo a `?password=` vindo do Supera ERP!) |
| **Serviço + Firewall Windows** | Instalação registra `Supera-Desk Service` (`start= auto`) e libera Entrada/Saída em todos os perfis (`profile=any`) |
| **Remoção White-Label** | Zero menção a `"Powered by RustDesk"`, zero link externo `rustdesk.com`, zero erro de API na porta `21114` |

> **Reutilização Multi-Clientes (focuSolution):** Ao disparar a GitHub Action manualmente (`workflow_dispatch`), é possível informar outro `id_server`, `relay_server` e `pub_key` para gerar binários dedicados para novos clientes da software house sem alterar uma linha de código.

---

## 2. Artefatos Gerados pela Pipeline (`.github/workflows/build-supera-desk.yml`)

1. **`Supera-Desk-Setup-Win64.exe`**: Executável único Windows 10/11 (64-bit). Funciona tanto em execução imediata (portátil) quanto como instalador de 1 clique (`--silent-install` ou botão **Instalar**), subindo o serviço permanente e liberando o Windows Firewall automaticamente.
2. **`Supera-Desk-Win64.msi`**: Pacote corporativo Windows Installer para implantação massiva via GPO / Active Directory / Intune.
3. **`Supera-Desk-Mac-AppleSilicon.dmg`**: Aplicativo nativo ARM64 (`Supera-Desk.app`) para Macs M1/M2/M3/M4 com captura `ScreenCaptureKit` e decodificação por hardware `VideoToolbox` (para suporte `Mac -> Windows` em altíssima fluidez).

---

## 3. Assinatura Digital Opcional (Windows SmartScreen & Apple Gatekeeper)

A pipeline já possui suporte nativo aos *GitHub Secrets* opcionais caso deseje assinar digitalmente os binários no futuro:
- `WINDOWS_PFX_BASE64` e `WINDOWS_PFX_PASSWORD` (Certificado Code Signing `.pfx` EV/OV via `signtool.exe` SHA-256).
- No macOS sem certificado Apple Developer ID ($99/ano), o `Supera-Desk.app` já recebe assinatura *ad-hoc* (`codesign -s -`), e o conector do Supera ERP remove automaticamente o atributo de quarentena (`xattr -dr com.apple.quarantine /Applications/Supera-Desk.app`).
