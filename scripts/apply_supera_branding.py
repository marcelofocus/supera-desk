#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicador determinístico de White-Label e Infraestrutura Privada do Supera-Desk
sobre a árvore upstream do RustDesk 1.3.8 (Rust + Flutter Desktop Windows x64 e macOS arm64/x86_64).

Garantias arquiteturais:
1. Servidor ID (`hbbs`), Relay (`hbbr`) e Chave Pública Ed25519 compilados nativamente no binário
   (`superadesk.ipog.cloud` + `MwoPxCW4rXbAXrMf0F9Mmo5NOqpYp1EVtTZAeJORUpo=`, parametrizáveis via ENV p/ multi-clientes focuSolution);
2. Identidade 100% Supera-Desk (`APP_NAME = "Supera-Desk"`, `ORG = "br.com.focusolution"`, zero menção a
   "Powered by RustDesk", zero link `rustdesk.com`, zero erro de "API server" em porta 21114);
3. Interface Desktop completa de mão dupla (`Mac -> Windows` e `Windows -> Windows`) com codec GPU (`hwcodec`),
   conexão UDP direta (`direct-server = Y`) e protocolo URI `supera-desk://` + `superadesk://` (com suporte a `?password=`);
4. Instalação Windows cria Serviço `Supera-Desk` (`start= auto`) e libera automaticamente Firewall de Entrada e Saída (`profile=any`).
"""
import argparse
import os
import re
import shutil
import sys
from pathlib import Path


def _replace_exact(content: str, target: str, replacement: str, label: str) -> str:
    if target not in content:
        raise RuntimeError(f"[Supera-Desk Patch Error] Trecho esperado não encontrado em {label}:\n{target!r}")
    return content.replace(target, replacement, 1)


def patch_hbb_common_config(path: Path, cfg: dict[str, str]) -> None:
    src = path.read_text(encoding="utf-8")
    app_name = cfg["app_name"]
    org = cfg["org"]
    id_srv = cfg["id_server"]
    relay_srv = cfg["relay_server"]
    pub_key = cfg["pub_key"]
    portal_url = cfg["portal_url"]

    src = _replace_exact(
        src,
        'pub static ref ORG: RwLock<String> = RwLock::new("com.carriez".to_owned());',
        f'pub static ref ORG: RwLock<String> = RwLock::new("{org}".to_owned());',
        "config.rs::ORG",
    )
    src = _replace_exact(
        src,
        'pub static ref PROD_RENDEZVOUS_SERVER: RwLock<String> = RwLock::new("".to_owned());',
        f'pub static ref PROD_RENDEZVOUS_SERVER: RwLock<String> = RwLock::new("{id_srv}".to_owned());',
        "config.rs::PROD_RENDEZVOUS_SERVER",
    )
    src = _replace_exact(
        src,
        'pub static ref APP_NAME: RwLock<String> = RwLock::new("RustDesk".to_owned());',
        f'pub static ref APP_NAME: RwLock<String> = RwLock::new("{app_name}".to_owned());',
        "config.rs::APP_NAME",
    )
    src = _replace_exact(
        src,
        'pub static ref DEFAULT_SETTINGS: RwLock<HashMap<String, String>> = Default::default();',
        (
            "pub static ref DEFAULT_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(HashMap::from([\n"
            f'        ("custom-rendezvous-server".to_owned(), "{id_srv}".to_owned()),\n'
            f'        ("relay-server".to_owned(), "{relay_srv}".to_owned()),\n'
            f'        ("key".to_owned(), "{pub_key}".to_owned()),\n'
            '        ("direct-server".to_owned(), "Y".to_owned()),\n'
            '        ("enable-hwcodec".to_owned(), "Y".to_owned()),\n'
            '        ("enable-abr".to_owned(), "Y".to_owned()),\n'
            '        ("verification-method".to_owned(), "use-both-passwords".to_owned()),\n'
            "    ]));"
        ),
        "config.rs::DEFAULT_SETTINGS",
    )
    src = _replace_exact(
        src,
        'pub static ref BUILTIN_SETTINGS: RwLock<HashMap<String, String>> = Default::default();',
        (
            "pub static ref BUILTIN_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(HashMap::from([\n"
            '        ("remove-preset-password-warning".to_owned(), "Y".to_owned()),\n'
            '        ("hide-help-cards".to_owned(), "Y".to_owned()),\n'
            "    ]));"
        ),
        "config.rs::BUILTIN_SETTINGS",
    )
    src = _replace_exact(
        src,
        'pub const LINK_DOCS_HOME: &str = "https://rustdesk.com/docs/en/";',
        f'pub const LINK_DOCS_HOME: &str = "{portal_url}";',
        "config.rs::LINK_DOCS_HOME",
    )
    src = _replace_exact(
        src,
        'pub const LINK_DOCS_X11_REQUIRED: &str = "https://rustdesk.com/docs/en/manual/linux/#x11-required";',
        f'pub const LINK_DOCS_X11_REQUIRED: &str = "{portal_url}";',
        "config.rs::LINK_DOCS_X11_REQUIRED",
    )
    src = _replace_exact(
        src,
        'pub const RENDEZVOUS_SERVERS: &[&str] = &["rs-ny.rustdesk.com"];',
        f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{id_srv}"];',
        "config.rs::RENDEZVOUS_SERVERS",
    )
    src = _replace_exact(
        src,
        'pub const RS_PUB_KEY: &str = "OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw=";',
        f'pub const RS_PUB_KEY: &str = "{pub_key}";',
        "config.rs::RS_PUB_KEY",
    )
    path.write_text(src, encoding="utf-8")


def patch_src_common(path: Path) -> None:
    src = path.read_text(encoding="utf-8")
    # 1. Nunca aponta para http://<id_server>:21114 nem https://admin.rustdesk.com quando não há servidor API Pro configurado
    old_api_block = """    let s0 = get_custom_rendezvous_server(custom);
    if !s0.is_empty() {
        let s = crate::increase_port(&s0, -2);
        if s == s0 {
            return format!("http://{}:{}", s, config::RENDEZVOUS_PORT - 2);
        } else {
            return format!("http://{}", s);
        }
    }
    "https://admin.rustdesk.com".to_owned()"""
    src = _replace_exact(
        src,
        old_api_block,
        '    let _ = custom;\n    "".to_owned()',
        "src/common.rs::get_api_server_",
    )
    # 2. Desativa checagem de versão contra github.com/rustdesk/rustdesk
    if "pub fn check_software_update()" in src:
        src = _replace_exact(
            src,
            "pub fn check_software_update() {",
            "pub fn check_software_update() { if !is_rustdesk() { return; }",
            "src/common.rs::check_software_update",
        )
    path.write_text(src, encoding="utf-8")


def patch_windows_platform(path: Path, cfg: dict[str, str]) -> None:
    src = path.read_text(encoding="utf-8")
    company = cfg["company_name"]
    # Isola GUID de instalação para conviver sem conflito com eventual RustDesk antigo na máquina Windows
    src = _replace_exact(
        src,
        'const IS1: &str = "{54E86BC2-6C85-41F3-A9EB-1A94AC9B1F93}_is1";',
        'const IS1: &str = "{8A4F9E21-7C3B-4D19-9E52-6F01B83D4A77}_is1";',
        "windows.rs::IS1",
    )
    # Registra ambos os protocolos URI (`supera-desk://` e `superadesk://`) e libera Firewall Windows em todos os perfis (`profile=any`)
    old_after = r"""    reg add HKEY_CLASSES_ROOT\\{ext}\\shell\\open\\command /f /ve /t REG_SZ /d \"\\\"{exe}\\\" \\\"%%1\\\"\"
    netsh advfirewall firewall add rule name=\"{app_name} Service\" dir=out action=allow program=\"{exe}\" enable=yes
    netsh advfirewall firewall add rule name=\"{app_name} Service\" dir=in action=allow program=\"{exe}\" enable=yes"""
    new_after = r"""    reg add HKEY_CLASSES_ROOT\\{ext}\\shell\\open\\command /f /ve /t REG_SZ /d \"\\\"{exe}\\\" \\\"%%1\\\"\"
    reg add HKEY_CLASSES_ROOT\\superadesk /f
    reg add HKEY_CLASSES_ROOT\\superadesk /f /v \"URL Protocol\" /t REG_SZ /d \"\"
    reg add HKEY_CLASSES_ROOT\\superadesk\\shell\\open\\command /f /ve /t REG_SZ /d \"\\\"{exe}\\\" \\\"%%1\\\"\"
    netsh advfirewall firewall delete rule name=\"{app_name} Service\"
    netsh advfirewall firewall add rule name=\"{app_name} Service\" dir=out action=allow program=\"{exe}\" enable=yes profile=any
    netsh advfirewall firewall add rule name=\"{app_name} Service\" dir=in action=allow program=\"{exe}\" enable=yes profile=any"""
    src = _replace_exact(src, old_after, new_after, "windows.rs::get_after_install")

    src = _replace_exact(
        src,
        r'reg add {subkey} /f /v Publisher /t REG_SZ /d \"{app_name}\"',
        rf'reg add {{subkey}} /f /v Publisher /t REG_SZ /d \"{company}\"',
        "windows.rs::Publisher",
    )
    src = _replace_exact(
        src,
        r"    reg delete HKEY_CLASSES_ROOT\\{ext} /f",
        r"    reg delete HKEY_CLASSES_ROOT\\{ext} /f" + "\n" + r"    reg delete HKEY_CLASSES_ROOT\\superadesk /f",
        "windows.rs::get_before_uninstall",
    )
    path.write_text(src, encoding="utf-8")


def patch_macos_platform(macos_rs: Path, build_py: Path, xcconfig: Path, pbxproj: Path, info_plist: Path, cfg: dict[str, str]) -> None:
    app_name = cfg["app_name"]
    bundle_id = cfg["bundle_id"]
    copyright_str = cfg["copyright"]

    # 1. src/platform/macos.rs — garante que LaunchDaemons/LaunchAgents substituam `com.carriez` pelo ORG do Supera-Desk
    m_src = macos_rs.read_text(encoding="utf-8")
    m_src = _replace_exact(
        m_src,
        'fn correct_app_name(s: &str) -> String {\n    let s = s.replace("rustdesk", &crate::get_app_name().to_lowercase());\n    let s = s.replace("RustDesk", &crate::get_app_name());\n    s\n}',
        (
            "fn correct_app_name(s: &str) -> String {\n"
            '    let s = s.replace("com.carriez", &hbb_common::config::ORG.read().unwrap());\n'
            '    let s = s.replace("rustdesk", &crate::get_app_name().to_lowercase());\n'
            '    let s = s.replace("RustDesk", &crate::get_app_name());\n'
            "    s\n"
            "}"
        ),
        "macos.rs::correct_app_name",
    )
    macos_rs.write_text(m_src, encoding="utf-8")

    # 2. build.py — atualiza cópia do binário `service` para `Supera-Desk.app`
    b_src = build_py.read_text(encoding="utf-8")
    b_src = _replace_exact(
        b_src,
        "cp -rf ../target/release/service ./build/macos/Build/Products/Release/RustDesk.app/Contents/MacOS/",
        f"cp -rf ../target/release/service ./build/macos/Build/Products/Release/{app_name}.app/Contents/MacOS/",
        "build.py::macos_service_copy",
    )
    build_py.write_text(b_src, encoding="utf-8")

    # 3. AppInfo.xcconfig
    if xcconfig.is_file():
        xc = xcconfig.read_text(encoding="utf-8")
        xc = re.sub(r"^PRODUCT_NAME\s*=.*$", f"PRODUCT_NAME = {app_name}", xc, flags=re.MULTILINE)
        xc = re.sub(r"^PRODUCT_BUNDLE_IDENTIFIER\s*=.*$", f"PRODUCT_BUNDLE_IDENTIFIER = {bundle_id}", xc, flags=re.MULTILINE)
        xc = re.sub(r"^PRODUCT_COPYRIGHT\s*=.*$", f"PRODUCT_COPYRIGHT = {copyright_str}", xc, flags=re.MULTILINE)
        xcconfig.write_text(xc, encoding="utf-8")

    # 4. Runner.xcodeproj/project.pbxproj
    if pbxproj.is_file():
        pbx = pbxproj.read_text(encoding="utf-8")
        pbx = pbx.replace("com.carriez.rustdesk", bundle_id)
        pbx = pbx.replace("path = RustDesk.app;", f'path = "{app_name}.app";')
        pbx = pbx.replace('PRODUCT_NAME = "$(TARGET_NAME)";', f'PRODUCT_NAME = "{app_name}";')
        pbxproj.write_text(pbx, encoding="utf-8")

    # 5. Info.plist — esquemas `supera-desk://` e `superadesk://` + descrições em Português
    plist = info_plist.read_text(encoding="utf-8")
    plist = _replace_exact(
        plist,
        "\t\t\t<key>CFBundleURLName</key>\n\t\t\t<string>com.carriez.rustdesk</string>\n\t\t\t<key>CFBundleURLSchemes</key>\n\t\t\t<array>\n\t\t\t\t<string>rustdesk</string>\n\t\t\t</array>",
        (
            f"\t\t\t<key>CFBundleURLName</key>\n\t\t\t<string>{bundle_id}</string>\n"
            "\t\t\t<key>CFBundleURLSchemes</key>\n\t\t\t<array>\n"
            f"\t\t\t\t<string>{app_name.lower()}</string>\n"
            "\t\t\t\t<string>superadesk</string>\n"
            "\t\t\t</array>"
        ),
        "Info.plist::CFBundleURLSchemes",
    )
    plist = plist.replace(
        "Record the sound from microphone for the purpose of the remote desktop.",
        "Permite transmissão de áudio durante sessões autorizadas de suporte remoto Supera-Desk.",
    )
    if "<key>CFBundleDisplayName</key>" not in plist:
        plist = plist.replace(
            "<key>CFBundleName</key>",
            f"<key>CFBundleDisplayName</key>\n\t<string>{app_name}</string>\n\t<key>CFBundleName</key>",
            1,
        )
    info_plist.write_text(plist, encoding="utf-8")


def patch_windows_metadata_and_packers(
    runner_rc: Path,
    portable_main: Path,
    portable_build: Path,
    msi_preprocess: Path,
    cfg: dict[str, str],
) -> None:
    app_name = cfg["app_name"]
    company = cfg["company_name"]
    copyright_str = cfg["copyright"]
    portal_url = cfg["portal_url"]

    # 1. flutter/windows/runner/Runner.rc
    rc = runner_rc.read_text(encoding="utf-8")
    rc = _replace_exact(rc, 'VALUE "CompanyName", "Purslane Ltd" "\\0"', f'VALUE "CompanyName", "{company}" "\\0"', "Runner.rc::CompanyName")
    rc = _replace_exact(
        rc,
        'VALUE "FileDescription", "RustDesk Remote Desktop" "\\0"',
        f'VALUE "FileDescription", "{app_name} - Suporte Remoto Corporativo" "\\0"',
        "Runner.rc::FileDescription",
    )
    rc = _replace_exact(rc, 'VALUE "InternalName", "rustdesk" "\\0"', f'VALUE "InternalName", "{app_name}" "\\0"', "Runner.rc::InternalName")
    rc = _replace_exact(
        rc,
        'VALUE "LegalCopyright", "Copyright © 2025 Purslane Ltd. All rights reserved." "\\0"',
        f'VALUE "LegalCopyright", "{copyright_str}" "\\0"',
        "Runner.rc::LegalCopyright",
    )
    rc = _replace_exact(
        rc,
        'VALUE "OriginalFilename", "rustdesk.exe" "\\0"',
        f'VALUE "OriginalFilename", "{app_name}.exe" "\\0"',
        "Runner.rc::OriginalFilename",
    )
    rc = _replace_exact(rc, 'VALUE "ProductName", "RustDesk" "\\0"', f'VALUE "ProductName", "{app_name}" "\\0"', "Runner.rc::ProductName")
    runner_rc.write_text(rc, encoding="utf-8")

    # 2. libs/portable/src/main.rs — pasta temporária própria `%TEMP%\supera_desk`
    pm = portable_main.read_text(encoding="utf-8")
    pm = _replace_exact(pm, 'const APP_PREFIX: &str = "rustdesk";', 'const APP_PREFIX: &str = "supera_desk";', "portable/main.rs::APP_PREFIX")
    portable_main.write_text(pm, encoding="utf-8")

    # 3. libs/portable/build.rs — grava VERSIONINFO Supera-Desk também no instalador portátil `.exe`!
    if portable_build.is_file():
        pb = portable_build.read_text(encoding="utf-8")
        pb = _replace_exact(
            pb,
            '.set_manifest_file("../../res/manifest.xml");',
            (
                '.set_manifest_file("../../res/manifest.xml")\n'
                f'            .set("ProductName", "{app_name}")\n'
                f'            .set("FileDescription", "{app_name} - Suporte Remoto Corporativo")\n'
                f'            .set("CompanyName", "{company}")\n'
                f'            .set("LegalCopyright", "{copyright_str}")\n'
                f'            .set("OriginalFilename", "{app_name}-Setup-Win64.exe");'
            ),
            "portable/build.rs::winres",
        )
        portable_build.write_text(pb, encoding="utf-8")

    # 4. res/msi/preprocess.py — links institucionais Supera ERP no Painel de Controle do Windows
    mp = msi_preprocess.read_text(encoding="utf-8")
    mp = mp.replace("https://github.com/rustdesk/rustdesk/issues/", portal_url)
    mp = mp.replace("https://github.com/rustdesk/rustdesk", portal_url)
    msi_preprocess.write_text(mp, encoding="utf-8")


def patch_flutter_ui(common_dart: Path, home_dart: Path) -> None:
    # 1. flutter/lib/common.dart:
    #    - Paleta corporativa Supera ERP (#0284C7 / #0369A1)
    #    - Remove 100% `loadPowered` ("Powered by RustDesk" / rustdesk.com)
    #    - Suporta `supera-desk://` e `superadesk://` nativamente no handler de links!
    cd = common_dart.read_text(encoding="utf-8")
    cd = _replace_exact(
        cd,
        """  static const Color accent = Color(0xFF0071FF);
  static const Color accent50 = Color(0x770071FF);
  static const Color accent80 = Color(0xAA0071FF);
  static const Color canvasColor = Color(0xFF212121);
  static const Color border = Color(0xFFCCCCCC);
  static const Color idColor = Color(0xFF00B6F0);
  static const Color darkGray = Color.fromARGB(255, 148, 148, 148);
  static const Color cmIdColor = Color(0xFF21790B);
  static const Color dark = Colors.black87;
  static const Color button = Color(0xFF2C8CFF);""",
        """  static const Color accent = Color(0xFF0284C7);
  static const Color accent50 = Color(0x770284C7);
  static const Color accent80 = Color(0xAA0284C7);
  static const Color canvasColor = Color(0xFF0F172A);
  static const Color border = Color(0xFFCBD5E1);
  static const Color idColor = Color(0xFF0284C7);
  static const Color darkGray = Color.fromARGB(255, 100, 116, 139);
  static const Color cmIdColor = Color(0xFF059669);
  static const Color dark = Color(0xFF0F172A);
  static const Color button = Color(0xFF0284C7);""",
        "common.dart::MyTheme",
    )

    old_powered = """Widget loadPowered(BuildContext context) {
  return MouseRegion(
    cursor: SystemMouseCursors.click,
    child: GestureDetector(
      onTap: () {
        launchUrl(Uri.parse('https://rustdesk.com'));
      },
      child: Opacity(
          opacity: 0.5,
          child: Text(
            translate("powered_by_me"),
            overflow: TextOverflow.clip,
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(fontSize: 9, decoration: TextDecoration.underline),
          )),
    ),
  ).marginOnly(top: 6);
}"""
    cd = _replace_exact(
        cd,
        old_powered,
        "Widget loadPowered(BuildContext context) {\n  return const SizedBox.shrink();\n}",
        "common.dart::loadPowered",
    )

    cd = _replace_exact(
        cd,
        "if (args[0].startsWith(bind.mainUriPrefixSync())) {",
        "if (args[0].startsWith(bind.mainUriPrefixSync()) || args[0].toLowerCase().startsWith('superadesk://') || args[0].toLowerCase().startsWith('supera-desk://')) {",
        "common.dart::handleUriLink",
    )
    common_dart.write_text(cd, encoding="utf-8")

    # 2. flutter/lib/desktop/pages/desktop_home_page.dart:
    #    - Remove bloco `if (bind.isCustomClient()) Align(child: loadPowered(context))`
    #    - Substitui `borderColor` pelo azul Supera e remove URL `rustdesk.com/download`
    hd = home_dart.read_text(encoding="utf-8")
    hd = _replace_exact(
        hd,
        "const borderColor = Color(0xFF2F65BA);",
        "const borderColor = Color(0xFF0284C7);",
        "desktop_home_page.dart::borderColor",
    )
    hd = _replace_exact(
        hd,
        """      if (bind.isCustomClient())
        Align(
          alignment: Alignment.center,
          child: loadPowered(context),
        ),""",
        "",
        "desktop_home_page.dart::loadPoweredCall",
    )
    hd = hd.replace("https://rustdesk.com/download", "https://supera.ipog.cloud")
    home_dart.write_text(hd, encoding="utf-8")


def copy_brand_assets(repo_root: Path, assets_dir: Path) -> None:
    mappings = [
        ("logo.png", repo_root / "flutter/assets/logo.png"),
        ("icon.png", repo_root / "flutter/assets/icon.png"),
        ("icon.svg", repo_root / "flutter/assets/icon.svg"),
        ("logo.svg", repo_root / "res/logo.svg"),
        ("logo.svg", repo_root / "res/logo-header.svg"),
        ("scalable.svg", repo_root / "res/scalable.svg"),
        ("icon.png", repo_root / "res/icon.png"),
        ("mac-icon.png", repo_root / "res/mac-icon.png"),
        ("32x32.png", repo_root / "res/32x32.png"),
        ("64x64.png", repo_root / "res/64x64.png"),
        ("128x128.png", repo_root / "res/128x128.png"),
        ("128x128@2x.png", repo_root / "res/128x128@2x.png"),
        ("icon.ico", repo_root / "res/icon.ico"),
        ("tray-icon.ico", repo_root / "res/tray-icon.ico"),
        ("app_icon.ico", repo_root / "flutter/windows/runner/resources/app_icon.ico"),
        ("mac-tray-dark-x2.png", repo_root / "res/mac-tray-dark-x2.png"),
        ("mac-tray-light-x2.png", repo_root / "res/mac-tray-light-x2.png"),
        ("AppIcon.icns", repo_root / "flutter/macos/Runner/AppIcon.icns"),
    ]
    for src_name, dst_path in mappings:
        src_file = assets_dir / src_name
        if not src_file.is_file():
            raise RuntimeError(f"[Supera-Desk Assets] Arquivo obrigatório ausente: {src_file}")
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_path)


def apply_all(repo_root: Path, assets_dir: Path, cfg: dict[str, str]) -> None:
    patch_hbb_common_config(repo_root / "libs/hbb_common/src/config.rs", cfg)
    patch_src_common(repo_root / "src/common.rs")
    patch_windows_platform(repo_root / "src/platform/windows.rs", cfg)
    patch_macos_platform(
        repo_root / "src/platform/macos.rs",
        repo_root / "build.py",
        repo_root / "flutter/macos/Runner/Configs/AppInfo.xcconfig",
        repo_root / "flutter/macos/Runner.xcodeproj/project.pbxproj",
        repo_root / "flutter/macos/Runner/Info.plist",
        cfg,
    )
    patch_windows_metadata_and_packers(
        repo_root / "flutter/windows/runner/Runner.rc",
        repo_root / "libs/portable/src/main.rs",
        repo_root / "libs/portable/build.rs",
        repo_root / "res/msi/preprocess.py",
        cfg,
    )
    patch_flutter_ui(
        repo_root / "flutter/lib/common.dart",
        repo_root / "flutter/lib/desktop/pages/desktop_home_page.dart",
    )
    copy_brand_assets(repo_root, assets_dir)
    print(
        f"[Supera-Desk] White-label aplicado com sucesso!\n"
        f"  App:        {cfg['app_name']} ({cfg['bundle_id']})\n"
        f"  ID Server:  {cfg['id_server']}\n"
        f"  Relay:      {cfg['relay_server']}\n"
        f"  PubKey:     {cfg['pub_key'][:12]}...{cfg['pub_key'][-6:]}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Aplica o white-label corporativo Supera-Desk na árvore RustDesk 1.3.8")
    parser.add_argument("--rustdesk-dir", required=True, help="Diretório raiz do checkout rustdesk 1.3.8")
    parser.add_argument(
        "--assets-dir",
        default=str(Path(__file__).resolve().parent.parent / "assets"),
        help="Diretório com os ícones e logos do Supera-Desk",
    )
    args = parser.parse_args()

    app_name = os.environ.get("SUPERA_APP_NAME", "Supera-Desk").strip()
    org = os.environ.get("SUPERA_ORG", "br.com.focusolution").strip()
    id_server = os.environ.get("SUPERA_ID_SERVER", "superadesk.ipog.cloud").strip()
    relay_server = os.environ.get("SUPERA_RELAY_SERVER", id_server).strip() or id_server
    pub_key = os.environ.get("SUPERA_PUB_KEY", "MwoPxCW4rXbAXrMf0F9Mmo5NOqpYp1EVtTZAeJORUpo=").strip()
    portal_url = os.environ.get("SUPERA_PORTAL_URL", "https://supera.ipog.cloud").strip()
    company_name = os.environ.get("SUPERA_COMPANY_NAME", "Supera ERP - focuSolution").strip()
    copyright_str = os.environ.get(
        "SUPERA_COPYRIGHT",
        "Copyright © 2026 Supera ERP / focuSolution. Todos os direitos reservados.",
    ).strip()

    cfg = {
        "app_name": app_name,
        "org": org,
        "bundle_id": f"{org}.{app_name.lower()}",
        "id_server": id_server,
        "relay_server": relay_server,
        "pub_key": pub_key,
        "portal_url": portal_url,
        "company_name": company_name,
        "copyright": copyright_str,
    }

    apply_all(Path(args.rustdesk_dir).resolve(), Path(args.assets_dir).resolve(), cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
