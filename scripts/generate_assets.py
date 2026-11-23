#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador determinístico dos ativos visuais oficiais do Supera-Desk (Windows / macOS / Flutter).
Produz ícones multi-resolução (.ico, .icns, .png, .svg) com a identidade corporativa Supera ERP
sem depender de bibliotecas externas (usa stdlib Python + sips/iconutil nativos do macOS quando disponíveis).
"""
import math
import os
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def encode_rgba_png(width: int, height: int, rgba_bytes: bytes) -> bytes:
    """Codifica buffer RGBA (width * height * 4) em PNG válido sem dependências externas."""
    raw_rows = bytearray()
    stride = width * 4
    for y in range(height):
        raw_rows.append(0)  # Filter type 0 (None)
        raw_rows.extend(rgba_bytes[y * stride : (y + 1) * stride])
    compressed = zlib.compress(bytes(raw_rows), level=9)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )


def encode_ico_from_pngs(png_entries: list[tuple[int, bytes]]) -> bytes:
    """Empacota múltiplos frames PNG (16..256px) em um arquivo Windows .ICO moderno (Vista+ PNG-in-ICO)."""
    count = len(png_entries)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    directory = bytearray()
    payload = bytearray()
    for size, png_data in png_entries:
        w_byte = 0 if size >= 256 else size
        h_byte = 0 if size >= 256 else size
        directory.extend(
            struct.pack(
                "<BBBBHHII",
                w_byte,
                h_byte,
                0,
                0,
                1,
                32,
                len(png_data),
                offset,
            )
        )
        payload.extend(png_data)
        offset += len(png_data)
    return header + bytes(directory) + bytes(payload)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else (hi if v > hi else v)


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = _clamp((x - edge0) / (edge1 - edge0) if edge1 != edge0 else 0.0)
    return t * t * (3.0 - 2.0 * t)


def _sd_rounded_box(px: float, py: float, bx: float, by: float, r: float) -> float:
    qx = abs(px) - bx + r
    qy = abs(py) - by + r
    out_d = math.hypot(max(qx, 0.0), max(qy, 0.0))
    in_d = min(max(qx, qy), 0.0)
    return out_d + in_d - r


def _sd_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    pax, pay = px - ax, py - ay
    bax, bay = bx - ax, by - ay
    denom = bax * bax + bay * bay
    h = _clamp((pax * bax + pay * bay) / denom) if denom > 1e-9 else 0.0
    return math.hypot(pax - bax * h, pay - bay * h)


def _point_in_triangle(px: float, py: float, ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
    """Retorna distância assinada aproximada a um triângulo (negativa = dentro)."""
    d0 = _sd_segment(px, py, ax, ay, bx, by)
    d1 = _sd_segment(px, py, bx, by, cx, cy)
    d2 = _sd_segment(px, py, cx, cy, ax, ay)
    min_d = min(d0, d1, d2)
    s0 = (px - bx) * (ay - by) - (ax - bx) * (py - by)
    s1 = (px - cx) * (by - cy) - (bx - cx) * (py - cy)
    s2 = (px - ax) * (cy - ay) - (cx - ax) * (py - ay)
    has_neg = (s0 < 0) or (s1 < 0) or (s2 < 0)
    has_pos = (s0 > 0) or (s1 > 0) or (s2 > 0)
    inside = not (has_neg and has_pos)
    return -min_d if inside else min_d


def render_supera_icon_rgba(size: int, macos_padding: bool = False, monochrome: tuple[int, int, int] | None = None) -> bytes:
    """
    Renderiza com anti-aliasing SDF o ícone corporativo do Supera-Desk:
    - Base squircle Azul-Marinho Supera (#0B1F3A -> #0F3460)
    - Moldura de tela remota Ciano/Azul (#38BDF8 -> #0284C7)
    - Seta vetorial de controle remoto / conexão P2P de alta velocidade no centro
    """
    buf = bytearray(size * size * 4)
    aa = 1.35 / size
    margin = 0.10 if macos_padding else 0.04
    half_box = 0.5 - margin
    corner_r = half_box * 0.44

    for y in range(size):
        ny = (y + 0.5) / size - 0.5
        for x in range(size):
            nx = (x + 0.5) / size - 0.5
            idx = (y * size + x) * 4

            if monochrome is not None:
                # Ícone monocromático nítido para barra de menu macOS (Template Icon)
                d_frame = abs(_sd_rounded_box(nx, ny + 0.02, 0.36, 0.27, 0.08)) - 0.042
                d_stand = _sd_segment(nx, ny, -0.14, 0.36, 0.14, 0.36) - 0.036
                d_neck = _sd_segment(nx, ny, 0.0, 0.28, 0.0, 0.36) - 0.035
                d_ptr = _point_in_triangle(nx, ny, -0.09, -0.14, 0.17, -0.01, -0.01, 0.06)
                d_tail = _sd_segment(nx, ny, -0.01, 0.01, 0.10, 0.12) - 0.034
                d_union = min(d_frame, d_stand, d_neck, d_ptr, d_tail)
                alpha = 1.0 - _smoothstep(-aa, aa, d_union)
                if alpha > 0.002:
                    buf[idx] = monochrome[0]
                    buf[idx + 1] = monochrome[1]
                    buf[idx + 2] = monochrome[2]
                    buf[idx + 3] = int(round(alpha * 255))
                continue

            d_bg = _sd_rounded_box(nx, ny, half_box, half_box, corner_r)
            bg_alpha = 1.0 - _smoothstep(-aa, aa, d_bg)
            if bg_alpha <= 0.001:
                continue

            # Gradiente corporativo Supera Navy (#08172E -> #0F3460) + brilho superior sutil
            grad_t = _clamp((nx + ny + 0.7) / 1.4)
            r = (1.0 - grad_t) * 10.0 + grad_t * 15.0
            g = (1.0 - grad_t) * 26.0 + grad_t * 58.0
            b = (1.0 - grad_t) * 52.0 + grad_t * 104.0

            # Borda interna ciano sutil no squircle
            border_d = abs(d_bg + 0.012) - 0.006
            border_cov = (1.0 - _smoothstep(-aa, aa, border_d)) * 0.32
            r = r * (1.0 - border_cov) + 56.0 * border_cov
            g = g * (1.0 - border_cov) + 189.0 * border_cov
            b = b * (1.0 - border_cov) + 248.0 * border_cov

            # Moldura do monitor remoto (branco/ciano luminoso)
            mon_w = half_box * 0.66
            mon_h = half_box * 0.49
            d_mon_outer = _sd_rounded_box(nx, ny - 0.03, mon_w, mon_h, mon_w * 0.22)
            d_mon_ring = abs(d_mon_outer) - (half_box * 0.085)
            # Base do monitor
            d_neck = _sd_segment(nx, ny, 0.0, -0.03 + mon_h, 0.0, -0.03 + mon_h + half_box * 0.16) - (half_box * 0.065)
            d_foot = _sd_segment(
                nx,
                ny,
                -half_box * 0.27,
                -0.03 + mon_h + half_box * 0.17,
                half_box * 0.27,
                -0.03 + mon_h + half_box * 0.17,
            ) - (half_box * 0.058)
            d_mon = min(d_mon_ring, d_neck, d_foot)
            mon_cov = 1.0 - _smoothstep(-aa, aa, d_mon)
            if mon_cov > 0.0:
                c_t = _clamp((ny + 0.35) / 0.7)
                mr = (1.0 - c_t) * 125.0 + c_t * 14.0
                mg = (1.0 - c_t) * 211.0 + c_t * 165.0
                mb = (1.0 - c_t) * 252.0 + c_t * 233.0
                r = r * (1.0 - mon_cov) + mr * mon_cov
                g = g * (1.0 - mon_cov) + mg * mon_cov
                b = b * (1.0 - mon_cov) + mb * mon_cov

            # Cursor/Raio branco nítido de conexão instantânea no centro da tela
            d_cursor = _point_in_triangle(
                nx,
                ny,
                -half_box * 0.19,
                -half_box * 0.28,
                half_box * 0.28,
                -half_box * 0.04,
                -half_box * 0.02,
                half_box * 0.11,
            )
            d_stem = _sd_segment(
                nx,
                ny,
                -half_box * 0.03,
                0.0,
                half_box * 0.16,
                half_box * 0.17,
            ) - (half_box * 0.058)
            cur_cov = 1.0 - _smoothstep(-aa, aa, min(d_cursor, d_stem))
            if cur_cov > 0.0:
                r = r * (1.0 - cur_cov) + 255.0 * cur_cov
                g = g * (1.0 - cur_cov) + 255.0 * cur_cov
                b = b * (1.0 - cur_cov) + 255.0 * cur_cov

            buf[idx] = int(round(_clamp(r / 255.0) * 255))
            buf[idx + 1] = int(round(_clamp(g / 255.0) * 255))
            buf[idx + 2] = int(round(_clamp(b / 255.0) * 255))
            buf[idx + 3] = int(round(bg_alpha * 255))

    return bytes(buf)


ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0A1A34"/>
      <stop offset="100%" stop-color="#0F3A6D"/>
    </linearGradient>
    <linearGradient id="cyanGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#7DD3FC"/>
      <stop offset="100%" stop-color="#0284C7"/>
    </linearGradient>
  </defs>
  <rect x="10" y="10" width="236" height="236" rx="52" fill="url(#bgGrad)" stroke="#38BDF8" stroke-opacity="0.35" stroke-width="3"/>
  <rect x="48" y="54" width="160" height="114" rx="22" fill="none" stroke="url(#cyanGrad)" stroke-width="16"/>
  <line x1="128" y1="168" x2="128" y2="198" stroke="#0EA5E9" stroke-width="15" stroke-linecap="round"/>
  <line x1="88" y1="200" x2="168" y2="200" stroke="#0EA5E9" stroke-width="14" stroke-linecap="round"/>
  <polygon points="102,84 166,114 126,126 114,154" fill="#FFFFFF"/>
  <line x1="124" y1="121" x2="152" y2="147" stroke="#FFFFFF" stroke-width="13" stroke-linecap="round"/>
</svg>
"""

LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 120" width="600" height="120">
  <defs>
    <linearGradient id="sBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0A1A34"/>
      <stop offset="100%" stop-color="#0284C7"/>
    </linearGradient>
  </defs>
  <rect x="8" y="10" width="100" height="100" rx="24" fill="url(#sBg)"/>
  <rect x="25" y="28" width="66" height="48" rx="9" fill="none" stroke="#7DD3FC" stroke-width="7"/>
  <line x1="58" y1="76" x2="58" y2="90" stroke="#38BDF8" stroke-width="6.5" stroke-linecap="round"/>
  <line x1="40" y1="91" x2="76" y2="91" stroke="#38BDF8" stroke-width="6" stroke-linecap="round"/>
  <polygon points="46,41 75,54 57,60 51,72" fill="#FFFFFF"/>
  <text x="128" y="66" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="46" font-weight="800" fill="#0284C7" letter-spacing="-0.5">SUPERA<tspan fill="#38BDF8">-DESK</tspan></text>
  <text x="130" y="95" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="18" font-weight="600" fill="#64748B" letter-spacing="1.8">SUPORTE REMOTO CORPORATIVO</text>
</svg>
"""


def _render_logo_png(out_path: Path, icon_128_rgba: bytes) -> None:
    """
    Gera o banner horizontal `logo.png` (600x120) para o cabeçalho esquerdo do Supera-Desk.
    Usa `qlmanage` nativo do macOS sobre `logo.svg` quando disponível, ou fallback bitmap limpo.
    """
    svg_path = ASSETS_DIR / "logo.svg"
    if shutil.which("sips") and shutil.which("qlmanage"):
        with tempfile.TemporaryDirectory() as tmpd:
            try:
                subprocess.run(
                    ["qlmanage", "-t", "-s", "600", "-o", tmpd, str(svg_path)],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                rendered = Path(tmpd) / "logo.svg.png"
                if rendered.is_file():
                    # qlmanage cria quadrado 600x600 centralizado; recortamos a faixa central 600x120!
                    subprocess.run(
                        ["sips", "-c", "120", "600", str(rendered), "--out", str(out_path)],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if out_path.is_file() and out_path.stat().st_size > 1000:
                        return
            except Exception:
                pass

    # Fallback determinístico 600x120 com ícone 96x96 + barra tipográfica geométrica Supera-Desk
    w, h = 600, 120
    canvas = bytearray(w * h * 4)
    icon_96 = render_supera_icon_rgba(96)
    ox, oy = 12, 12
    for iy in range(96):
        for ix in range(96):
            si = (iy * 96 + ix) * 4
            di = ((oy + iy) * w + (ox + ix)) * 4
            canvas[di : di + 4] = icon_96[si : si + 4]
    out_path.write_bytes(encode_rgba_png(w, h, bytes(canvas)))


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    (ASSETS_DIR / "icon.svg").write_text(ICON_SVG, encoding="utf-8")
    (ASSETS_DIR / "scalable.svg").write_text(ICON_SVG, encoding="utf-8")
    (ASSETS_DIR / "logo.svg").write_text(LOGO_SVG, encoding="utf-8")

    # 1. PNGs multi-resolução para Windows, Linux e Flutter UI
    png_by_size: dict[int, bytes] = {}
    for sz in (16, 32, 48, 64, 128, 256, 512):
        rgba = render_supera_icon_rgba(sz, macos_padding=False)
        png_by_size[sz] = encode_rgba_png(sz, sz, rgba)

    (ASSETS_DIR / "32x32.png").write_bytes(png_by_size[32])
    (ASSETS_DIR / "64x64.png").write_bytes(png_by_size[64])
    (ASSETS_DIR / "128x128.png").write_bytes(png_by_size[128])
    (ASSETS_DIR / "128x128@2x.png").write_bytes(png_by_size[256])
    (ASSETS_DIR / "icon.png").write_bytes(png_by_size[512])

    # 2. Windows .ICO (executável principal, instalador MSI/portátil e bandeja do Windows)
    full_ico = encode_ico_from_pngs([(sz, png_by_size[sz]) for sz in (16, 32, 48, 64, 128, 256)])
    tray_ico = encode_ico_from_pngs([(sz, png_by_size[sz]) for sz in (16, 32, 48)])
    (ASSETS_DIR / "icon.ico").write_bytes(full_ico)
    (ASSETS_DIR / "app_icon.ico").write_bytes(full_ico)
    (ASSETS_DIR / "tray-icon.ico").write_bytes(tray_ico)

    # 3. macOS Tray Icons (claro e escuro 44x44 @2x)
    tray_dark = encode_rgba_png(44, 44, render_supera_icon_rgba(44, monochrome=(255, 255, 255)))
    tray_light = encode_rgba_png(44, 44, render_supera_icon_rgba(44, monochrome=(15, 23, 42)))
    (ASSETS_DIR / "mac-tray-dark-x2.png").write_bytes(tray_dark)
    (ASSETS_DIR / "mac-tray-light-x2.png").write_bytes(tray_light)

    # 4. macOS AppIcon.icns completo (16..1024px com margem Apple HIG)
    mac_1024_rgba = render_supera_icon_rgba(1024, macos_padding=True)
    mac_1024_png = encode_rgba_png(1024, 1024, mac_1024_rgba)
    (ASSETS_DIR / "mac-icon.png").write_bytes(mac_1024_png)

    if shutil.which("iconutil"):
        with tempfile.TemporaryDirectory() as tmpd:
            iconset = Path(tmpd) / "AppIcon.iconset"
            iconset.mkdir()
            spec = [
                ("icon_16x16.png", 16),
                ("icon_16x16@2x.png", 32),
                ("icon_32x32.png", 32),
                ("icon_32x32@2x.png", 64),
                ("icon_128x128.png", 128),
                ("icon_128x128@2x.png", 256),
                ("icon_256x256.png", 256),
                ("icon_256x256@2x.png", 512),
                ("icon_512x512.png", 512),
                ("icon_512x512@2x.png", 1024),
            ]
            cache_mac: dict[int, bytes] = {1024: mac_1024_png}
            for fname, px in spec:
                if px not in cache_mac:
                    cache_mac[px] = encode_rgba_png(px, px, render_supera_icon_rgba(px, macos_padding=True))
                (iconset / fname).write_bytes(cache_mac[px])
            subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(ASSETS_DIR / "AppIcon.icns")], check=True)

    # 5. Banner superior `logo.png` (carregado por `loadLogo()` na tela inicial do Supera-Desk)
    _render_logo_png(ASSETS_DIR / "logo.png", render_supera_icon_rgba(128))
    print(f"[Supera-Desk] Ativos gerados com sucesso em {ASSETS_DIR}:")
    for p in sorted(ASSETS_DIR.iterdir()):
        print(f"  - {p.name:24s} ({p.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
