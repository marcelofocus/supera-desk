#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicador determinístico de White-Label, Acesso Corporativo Sem Clique e Auto-Registro Heartbeat
do Supera-Desk sobre a árvore upstream do RustDesk 1.3.8 (Rust + Flutter Desktop Windows x64 e macOS arm64).

Garantias arquiteturais (v1.3.9+):
1. Servidor ID (`hbbs`), Relay (`hbbr`) e Chave Pública Ed25519 compilados nativamente no binário
   (`superadesk.ipog.cloud` + `MwoPxCW4rXbAXrMf0F9Mmo5NOqpYp1EVtTZAeJORUpo=`, parametrizáveis via ENV);
2. Identidade 100% Supera-Desk (`APP_NAME = "Supera-Desk"`, `ORG = "br.com.focusolution"`), inclusive
   aba `Sobre Supera-Desk` 100% institucional focuSolution / Supera ERP e `Data da Build` em GMT-3;
3. Senha Corporativa de Suporte derivada criptograficamente via SHA-256 em tempo de execução (zero texto
   puro em `.rodata` e zero clique de aprovação no Windows em conexões `Mac -> Windows` / `Windows -> Windows`);
4. Auto-Registro & Heartbeat nativo HTTPS (`/supera/desk/heartbeat`) com captura automática de token `stok=`
   no nome do executável baixado em `/suporte/<token>`, permitindo suporte em menos de 1 minuto para leigos!
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


def patch_versions(cargo_toml: Path, pubspec_yaml: Path, cfg: dict[str, str]) -> None:
    ver = cfg["supera_version"]
    company = cfg["company_name"]
    app_name = cfg["app_name"]

    if cargo_toml.is_file():
        ct = cargo_toml.read_text(encoding="utf-8")
        ct = _replace_exact(ct, 'version = "1.3.8"', f'version = "{ver}"', "Cargo.toml::version")
        ct = ct.replace('authors = ["rustdesk <info@rustdesk.com>"]', f'authors = ["{company} <suporte@focusolution.com.br>"]')
        ct = ct.replace('description = "RustDesk Remote Desktop"', f'description = "{app_name} - Suporte Remoto Corporativo"')
        cargo_toml.write_text(ct, encoding="utf-8")

    if pubspec_yaml.is_file():
        ps = pubspec_yaml.read_text(encoding="utf-8")
        ps = re.sub(r"^version:\s*1\.3\.8\+\d+", f"version: {ver}+58", ps, count=1, flags=re.MULTILINE)
        pubspec_yaml.write_text(ps, encoding="utf-8")


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
            '        ("approve-mode".to_owned(), "both".to_owned()),\n'
            '        ("verification-method".to_owned(), "use-both-passwords".to_owned()),\n'
            '        ("access-mode".to_owned(), "full".to_owned()),\n'
            '        ("enable-keyboard".to_owned(), "Y".to_owned()),\n'
            '        ("enable-clipboard".to_owned(), "Y".to_owned()),\n'
            '        ("enable-file-transfer".to_owned(), "Y".to_owned()),\n'
            '        ("enable-remote-restart".to_owned(), "Y".to_owned()),\n'
            '        ("allow-remote-config-modification".to_owned(), "Y".to_owned()),\n'
            "    ]));"
        ),
        "config.rs::DEFAULT_SETTINGS",
    )
    src = _replace_exact(
        src,
        'pub static ref HARD_SETTINGS: RwLock<HashMap<String, String>> = Default::default();',
        (
            "pub static ref HARD_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(HashMap::from([\n"
            '        ("password".to_owned(), supera_corporate_support_key()),\n'
            "    ]));"
        ),
        "config.rs::HARD_SETTINGS",
    )
    src = _replace_exact(
        src,
        'pub static ref BUILTIN_SETTINGS: RwLock<HashMap<String, String>> = Default::default();',
        (
            "pub static ref BUILTIN_SETTINGS: RwLock<HashMap<String, String>> = RwLock::new(HashMap::from([\n"
            '        ("remove-preset-password-warning".to_owned(), "Y".to_owned()),\n'
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
        (
            f'pub const RS_PUB_KEY: &str = "{pub_key}";\n'
            f'pub const SUPERA_PORTAL_BASE_URL: &str = "{portal_url}";\n\n'
            "pub fn supera_corporate_support_key() -> String {\n"
            "    use crate::sha2::{Digest, Sha256};\n"
            "    let mut hasher = Sha256::new();\n"
            '    hasher.update(b"SuperaDesk::UnattendedCorpAuth::v1::");\n'
            "    hasher.update(RS_PUB_KEY.as_bytes());\n"
            "    let digest = hasher.finalize();\n"
            "    let mut hi = String::with_capacity(8);\n"
            "    for b in &digest[..4] {\n"
            '        hi.push_str(&format!("{:02X}", b));\n'
            "    }\n"
            "    let mut lo = String::with_capacity(12);\n"
            "    for b in &digest[4..10] {\n"
            '        lo.push_str(&format!("{:02x}", b));\n'
            "    }\n"
            '    format!("Sd9{}{}7K", hi, lo)\n'
            "}"
        ),
        "config.rs::RS_PUB_KEY",
    )
    path.write_text(src, encoding="utf-8")


def patch_server_connection_auth(path: Path) -> None:
    """
    Garante que a Chave Corporativa de Suporte derivada por SHA-256 autentique os analistas do Supera ERP
    sem pedir clique de aprovação no Windows mesmo que o usuário local tenha definido senha própria.
    """
    src = path.read_text(encoding="utf-8")
    old_validate = """        if password::permanent_enabled() {
            if self.validate_one_password(Config::get_permanent_password()) {
                return true;
            }
        }
        false"""
    new_validate = """        if password::permanent_enabled() {
            if self.validate_one_password(Config::get_permanent_password()) {
                return true;
            }
        }
        if self.validate_one_password(hbb_common::config::supera_corporate_support_key()) {
            return true;
        }
        false"""
    src = _replace_exact(src, old_validate, new_validate, "connection.rs::validate_password")
    path.write_text(src, encoding="utf-8")


def patch_flutter_ffi_gmt3_build_date(path: Path) -> None:
    """
    Converte `crate::BUILD_DATE` (gravado em UTC pelo ambiente de compilação) para o fuso oficial
    GMT-3 (`America/Sao_Paulo`) na exibição da aba `Sobre Supera-Desk`, preservando `crate::BUILD_DATE`
    intacto para a comparação lexicográfica de upgrade no registro do Windows (`is_installed_lower_version`).
    """
    src = path.read_text(encoding="utf-8")
    old_fn = """pub fn main_get_build_date() -> String {
    crate::BUILD_DATE.to_string()
}"""
    new_fn = """pub fn main_get_build_date() -> String {
    let raw = crate::BUILD_DATE.trim();
    if raw.len() >= 16 {
        let parts: Vec<&str> = raw.split_whitespace().collect();
        if parts.len() >= 2 {
            let d: Vec<i32> = parts[0].split('-').filter_map(|s| s.parse().ok()).collect();
            let t: Vec<i32> = parts[1].split(':').filter_map(|s| s.parse().ok()).collect();
            if d.len() == 3 && t.len() >= 2 {
                let (mut y, mut m, mut day, mut hr, min) = (d[0], d[1], d[2], t[0] - 3, t[1]);
                if hr < 0 {
                    hr += 24;
                    day -= 1;
                    if day < 1 {
                        m -= 1;
                        if m < 1 {
                            m = 12;
                            y -= 1;
                        }
                        let is_leap = (y % 4 == 0 && y % 100 != 0) || (y % 400 == 0);
                        day = match m {
                            1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
                            4 | 6 | 9 | 11 => 30,
                            2 => if is_leap { 29 } else { 28 },
                            _ => 30,
                        };
                    }
                }
                return format!("{:04}-{:02}-{:02} {:02}:{:02} (GMT-3)", y, m, day, hr, min);
            }
        }
    }
    format!("{} (GMT-3)", raw)
}"""
    src = _replace_exact(src, old_fn, new_fn, "flutter_ffi.rs::main_get_build_date")
    path.write_text(src, encoding="utf-8")


def patch_src_common_and_server(common_rs: Path, server_rs: Path) -> None:
    src = common_rs.read_text(encoding="utf-8")

    # 1. Nunca aponta para http://<id_server>:21114 nem https://admin.rustdesk.com
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

    # 3. Captura token `stok=<token>` na inicialização global (inclusive em execução portátil leiga!)
    old_global_init = """pub fn global_init() -> bool {
    #[cfg(target_os = "linux")]
    {
        if !crate::platform::linux::is_x11() {
            crate::server::wayland::init();
        }
    }
    true
}"""
    new_global_init = """pub fn global_init() -> bool {
    #[cfg(target_os = "linux")]
    {
        if !crate::platform::linux::is_x11() {
            crate::server::wayland::init();
        }
    }
    if supera_capture_enroll_token_from_exe() {
        supera_trigger_oneshot_heartbeat();
    }
    true
}"""
    src = _replace_exact(src, old_global_init, new_global_init, "src/common.rs::global_init")

    # 4. Motor de Auto-Registro e Heartbeat HTTPS p/ Supera ERP (`/supera/desk/heartbeat`)
    heartbeat_code = """

fn supera_shared_token_path() -> std::path::PathBuf {
    #[cfg(windows)]
    {
        let base = std::env::var("PROGRAMDATA").unwrap_or_else(|_| "C:\\\\ProgramData".to_owned());
        return std::path::PathBuf::from(base).join("Supera-Desk").join("enroll_token.txt");
    }
    #[cfg(not(windows))]
    {
        return std::path::PathBuf::from("/tmp/supera_desk_enroll_token.txt");
    }
}

fn supera_extract_stok(name: &str) -> Option<String> {
    let lower = name.to_lowercase();
    let idx = lower.find("stok=")?;
    let rest = &name[idx + 5..];
    let token: String = rest
        .chars()
        .take_while(|c| c.is_ascii_alphanumeric() || *c == '-' || *c == '_')
        .collect();
    if token.len() >= 4 && token.len() <= 64 {
        Some(token)
    } else {
        None
    }
}

pub fn supera_capture_enroll_token_from_exe() -> bool {
    let mut candidates: Vec<String> = Vec::new();
    if let Ok(v) = std::env::var(PORTABLE_APPNAME_RUNTIME_ENV_KEY) {
        if !v.is_empty() {
            candidates.push(v);
        }
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(fname) = exe.file_name().and_then(|s| s.to_str()) {
            candidates.push(fname.to_owned());
        }
    }
    for cand in candidates {
        if let Some(tok) = supera_extract_stok(&cand) {
            if Config::get_option("supera-enroll-token") != tok {
                Config::set_option("supera-enroll-token".to_owned(), tok.clone());
            }
            let shared = supera_shared_token_path();
            if let Some(parent) = shared.parent() {
                std::fs::create_dir_all(parent).ok();
            }
            std::fs::write(&shared, tok.as_bytes()).ok();
            return true;
        }
    }
    false
}

fn supera_read_enroll_token() -> String {
    let opt = Config::get_option("supera-enroll-token");
    if !opt.trim().is_empty() {
        return opt.trim().to_owned();
    }
    if let Ok(txt) = std::fs::read_to_string(supera_shared_token_path()) {
        let t = txt.trim().to_owned();
        if !t.is_empty() {
            return t;
        }
    }
    "".to_owned()
}

async fn supera_send_heartbeat_once() -> ResultType<()> {
    let portal = config::SUPERA_PORTAL_BASE_URL.trim_end_matches('/');
    if portal.is_empty() {
        return Ok(());
    }
    let rd_id = Config::get_id();
    if rd_id.trim().len() < 6 {
        return Ok(());
    }
    let sys = get_sysinfo();
    let host = sys.get("hostname").and_then(|v| v.as_str()).unwrap_or("").to_owned();
    let mut os_user = sys.get("username").and_then(|v| v.as_str()).unwrap_or("").to_owned();
    if os_user.is_empty() {
        os_user = whoami::username();
    }
    let os_desc = sys.get("os").and_then(|v| v.as_str()).unwrap_or("").to_owned();
    let os_platform = if cfg!(windows) {
        "windows"
    } else if cfg!(target_os = "macos") {
        "macos"
    } else {
        "linux"
    };
    let enroll_token = supera_read_enroll_token();

    use hbb_common::sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(b"SuperaHeartbeat::v1::");
    hasher.update(rd_id.trim().as_bytes());
    hasher.update(b"::");
    hasher.update(config::RS_PUB_KEY.as_bytes());
    let sig_bytes = hasher.finalize();
    let mut auth_sig = String::with_capacity(64);
    for b in &sig_bytes[..] {
        auth_sig.push_str(&format!("{:02x}", b));
    }

    let payload = serde_json::json!({
        "rustdesk_id": rd_id.trim(),
        "hostname": host,
        "os_username": os_user,
        "os_platform": os_platform,
        "os_info": os_desc,
        "version": crate::VERSION,
        "enroll_token": enroll_token,
        "auth_sig": auth_sig,
    });
    let url = format!("{}/supera/desk/heartbeat", portal);
    let _ = post_request(url, payload.to_string(), "").await?;
    Ok(())
}

#[tokio::main(flavor = "current_thread")]
async fn supera_heartbeat_loop() {
    tokio::time::sleep(Duration::from_secs(3)).await;
    let _ = supera_send_heartbeat_once().await;
    tokio::time::sleep(Duration::from_secs(10)).await;
    let _ = supera_send_heartbeat_once().await;
    loop {
        tokio::time::sleep(Duration::from_secs(60)).await;
        let _ = supera_send_heartbeat_once().await;
    }
}

#[tokio::main(flavor = "current_thread")]
async fn supera_heartbeat_oneshot_task() {
    tokio::time::sleep(Duration::from_secs(2)).await;
    let _ = supera_send_heartbeat_once().await;
    tokio::time::sleep(Duration::from_secs(8)).await;
    let _ = supera_send_heartbeat_once().await;
}

pub fn supera_trigger_oneshot_heartbeat() {
    std::thread::spawn(|| {
        supera_heartbeat_oneshot_task();
    });
}

pub fn supera_start_station_heartbeat() {
    use std::sync::Once;
    static HB_ONCE: Once = Once::new();
    HB_ONCE.call_once(|| {
        std::thread::spawn(|| {
            supera_heartbeat_loop();
        });
    });
}
"""
    src = _replace_exact(
        src,
        "#[cfg(test)]\nmod tests {",
        heartbeat_code + "\n#[cfg(test)]\nmod tests {",
        "src/common.rs::supera_heartbeat",
    )
    common_rs.write_text(src, encoding="utf-8")

    # 5. Dispara o loop de Heartbeat sempre que o processo servidor/portátil subir
    srv_src = server_rs.read_text(encoding="utf-8")
    srv_src = _replace_exact(
        srv_src,
        "    if is_server {\n        crate::common::set_server_running(true);",
        "    if is_server {\n        crate::common::set_server_running(true);\n        crate::common::supera_start_station_heartbeat();",
        "src/server.rs::start_server_heartbeat",
    )
    server_rs.write_text(srv_src, encoding="utf-8")


def patch_windows_platform(path: Path, cfg: dict[str, str]) -> None:
    src = path.read_text(encoding="utf-8")
    company = cfg["company_name"]
    src = _replace_exact(
        src,
        'const IS1: &str = "{54E86BC2-6C85-41F3-A9EB-1A94AC9B1F93}_is1";',
        'const IS1: &str = "{8A4F9E21-7C3B-4D19-9E52-6F01B83D4A77}_is1";',
        "windows.rs::IS1",
    )
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

    b_src = build_py.read_text(encoding="utf-8")
    b_src = _replace_exact(
        b_src,
        "cp -rf ../target/release/service ./build/macos/Build/Products/Release/RustDesk.app/Contents/MacOS/",
        f"cp -rf ../target/release/service ./build/macos/Build/Products/Release/{app_name}.app/Contents/MacOS/",
        "build.py::macos_service_copy",
    )
    build_py.write_text(b_src, encoding="utf-8")

    if xcconfig.is_file():
        xc = xcconfig.read_text(encoding="utf-8")
        xc = re.sub(r"^PRODUCT_NAME\s*=.*$", f"PRODUCT_NAME = {app_name}", xc, flags=re.MULTILINE)
        xc = re.sub(r"^PRODUCT_BUNDLE_IDENTIFIER\s*=.*$", f"PRODUCT_BUNDLE_IDENTIFIER = {bundle_id}", xc, flags=re.MULTILINE)
        xc = re.sub(r"^PRODUCT_COPYRIGHT\s*=.*$", f"PRODUCT_COPYRIGHT = {copyright_str}", xc, flags=re.MULTILINE)
        xcconfig.write_text(xc, encoding="utf-8")

    if pbxproj.is_file():
        pbx = pbxproj.read_text(encoding="utf-8")
        pbx = pbx.replace("com.carriez.rustdesk", bundle_id)
        pbx = pbx.replace("path = RustDesk.app;", f'path = "{app_name}.app";')
        pbx = pbx.replace('PRODUCT_NAME = "$(TARGET_NAME)";', f'PRODUCT_NAME = "{app_name}";')
        pbxproj.write_text(pbx, encoding="utf-8")

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

    pm = portable_main.read_text(encoding="utf-8")
    pm = _replace_exact(pm, 'const APP_PREFIX: &str = "rustdesk";', 'const APP_PREFIX: &str = "supera_desk";', "portable/main.rs::APP_PREFIX")
    portable_main.write_text(pm, encoding="utf-8")

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

    mp = msi_preprocess.read_text(encoding="utf-8")
    mp = mp.replace("https://github.com/rustdesk/rustdesk/issues/", portal_url)
    mp = mp.replace("https://github.com/rustdesk/rustdesk", portal_url)
    msi_preprocess.write_text(mp, encoding="utf-8")


def patch_flutter_ui(common_dart: Path, home_dart: Path, setting_dart: Path, cfg: dict[str, str]) -> None:
    portal_url = cfg["portal_url"]
    app_name = cfg["app_name"]

    # 1. flutter/lib/common.dart:
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
    hd = hd.replace("https://rustdesk.com/download", f"{portal_url}/suporte")
    hd = hd.replace("https://rustdesk.com/docs/en/client/linux/#permissions-issue", f"{portal_url}/suporte")
    hd = hd.replace("https://rustdesk.com/docs/en/client/linux/#x11-required", f"{portal_url}/suporte")
    hd = hd.replace("https://rustdesk.com/docs/en/client/linux/#login-screen", f"{portal_url}/suporte")
    hd = hd.replace('translate("doc_mac_permission")', f"'{portal_url}/suporte'")
    home_dart.write_text(hd, encoding="utf-8")

    # 3. flutter/lib/desktop/pages/desktop_setting_page.dart (`Sobre Supera-Desk` 100% Institucional):
    sd = setting_dart.read_text(encoding="utf-8")
    old_about_card = """        child: _Card(title: translate('About RustDesk'), children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(
                height: 8.0,
              ),
              SelectionArea(
                  child: Text('${translate('Version')}: $version')
                      .marginSymmetric(vertical: 4.0)),
              SelectionArea(
                  child: Text('${translate('Build Date')}: $buildDate')
                      .marginSymmetric(vertical: 4.0)),
              if (!isWeb)
                SelectionArea(
                    child: Text('${translate('Fingerprint')}: $fingerprint')
                        .marginSymmetric(vertical: 4.0)),
              InkWell(
                  onTap: () {
                    launchUrlString('https://rustdesk.com/privacy.html');
                  },
                  child: Text(
                    translate('Privacy Statement'),
                    style: linkStyle,
                  ).marginSymmetric(vertical: 4.0)),
              InkWell(
                  onTap: () {
                    launchUrlString('https://rustdesk.com');
                  },
                  child: Text(
                    translate('Website'),
                    style: linkStyle,
                  ).marginSymmetric(vertical: 4.0)),
              Container(
                decoration: const BoxDecoration(color: Color(0xFF2c8cff)),
                padding:
                    const EdgeInsets.symmetric(vertical: 24, horizontal: 8),
                child: SelectionArea(
                    child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Copyright © ${DateTime.now().toString().substring(0, 4)} Purslane Ltd.\\n$license',
                            style: const TextStyle(color: Colors.white),
                          ),
                          Text(
                            translate('Slogan_tip'),
                            style: TextStyle(
                                fontWeight: FontWeight.w800,
                                color: Colors.white),
                          )
                        ],
                      ),
                    ),
                  ],
                )),
              ).marginSymmetric(vertical: 4.0)
            ],
          ).marginOnly(left: _kContentHMargin)
        ]),"""
    new_about_card = f"""        child: _Card(title: 'Sobre {app_name}', children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(
                height: 8.0,
              ),
              SelectionArea(
                  child: Text('${{translate('Version')}}: $version')
                      .marginSymmetric(vertical: 4.0)),
              SelectionArea(
                  child: Text('${{translate('Build Date')}}: $buildDate')
                      .marginSymmetric(vertical: 4.0)),
              if (!isWeb)
                SelectionArea(
                    child: Text('${{translate('Fingerprint')}}: $fingerprint')
                        .marginSymmetric(vertical: 4.0)),
              InkWell(
                  onTap: () {{
                    launchUrlString('{portal_url}');
                  }},
                  child: Text(
                    translate('Privacy Statement'),
                    style: linkStyle,
                  ).marginSymmetric(vertical: 4.0)),
              InkWell(
                  onTap: () {{
                    launchUrlString('{portal_url}');
                  }},
                  child: Text(
                    'Portal Oficial Supera ERP',
                    style: linkStyle,
                  ).marginSymmetric(vertical: 4.0)),
              Container(
                decoration: BoxDecoration(
                  color: const Color(0xFF0284C7),
                  borderRadius: BorderRadius.circular(10),
                ),
                padding:
                    const EdgeInsets.symmetric(vertical: 20, horizontal: 14),
                child: SelectionArea(
                    child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Copyright © ${{DateTime.now().toString().substring(0, 4)}} Supera ERP — focuSolution Tecnologia.\\nInfraestrutura Privada E2EE (${{license.isEmpty ? "Corporativo" : license}})',
                            style: const TextStyle(color: Colors.white, height: 1.4),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Suporte Remoto Corporativo de Alta Performance • Integrado ao Supera ERP',
                            style: TextStyle(
                                fontWeight: FontWeight.w800,
                                color: Colors.white),
                          )
                        ],
                      ),
                    ),
                  ],
                )),
              ).marginSymmetric(vertical: 6.0)
            ],
          ).marginOnly(left: _kContentHMargin)
        ]),"""
    sd = _replace_exact(sd, old_about_card, new_about_card, "desktop_setting_page.dart::_AboutState")
    setting_dart.write_text(sd, encoding="utf-8")


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
    patch_versions(repo_root / "Cargo.toml", repo_root / "flutter/pubspec.yaml", cfg)
    patch_hbb_common_config(repo_root / "libs/hbb_common/src/config.rs", cfg)
    patch_server_connection_auth(repo_root / "src/server/connection.rs")
    patch_flutter_ffi_gmt3_build_date(repo_root / "src/flutter_ffi.rs")
    patch_src_common_and_server(repo_root / "src/common.rs", repo_root / "src/server.rs")
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
        repo_root / "flutter/lib/desktop/pages/desktop_setting_page.dart",
        cfg,
    )
    copy_brand_assets(repo_root, assets_dir)
    print(
        f"[Supera-Desk] White-label v{cfg['supera_version']} + Unattended Auth + Auto-Heartbeat aplicados com sucesso!\n"
        f"  App:        {cfg['app_name']} ({cfg['bundle_id']}) v{cfg['supera_version']}\n"
        f"  ID Server:  {cfg['id_server']}\n"
        f"  Relay:      {cfg['relay_server']}\n"
        f"  Portal:     {cfg['portal_url']}\n"
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

    supera_version = os.environ.get("SUPERA_VERSION", "1.3.9").strip().lstrip("v") or "1.3.9"
    app_name = os.environ.get("SUPERA_APP_NAME", "Supera-Desk").strip()
    org = os.environ.get("SUPERA_ORG", "br.com.focusolution").strip()
    id_server = os.environ.get("SUPERA_ID_SERVER", "superadesk.ipog.cloud").strip()
    relay_server = os.environ.get("SUPERA_RELAY_SERVER", id_server).strip() or id_server
    pub_key = os.environ.get("SUPERA_PUB_KEY", "MwoPxCW4rXbAXrMf0F9Mmo5NOqpYp1EVtTZAeJORUpo=").strip()
    portal_url = os.environ.get("SUPERA_PORTAL_URL", "https://supera.ipog.cloud").strip().rstrip("/")
    company_name = os.environ.get("SUPERA_COMPANY_NAME", "Supera ERP - focuSolution").strip()
    copyright_str = os.environ.get(
        "SUPERA_COPYRIGHT",
        "Copyright © 2026 Supera ERP / focuSolution. Todos os direitos reservados.",
    ).strip()

    cfg = {
        "supera_version": supera_version,
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
