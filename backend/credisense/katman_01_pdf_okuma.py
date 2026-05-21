from __future__ import annotations

"""Katman 01 - PDF Okuma

Bu dosyanın tek görevi PDF dosyasından metin çıkarmaktır.

Bu katmanda yapılmayan işler:
- Belge türü belirleme
- Kimlik/bordro/banka alanı çıkarma
- Tutarlılık kontrolü
- Risk tahmini

PDF dosyalarının iç yapısı normal metin dosyalarından daha karmaşıktır. Bu yüzden dosyanın
alt kısmında bazı teknik yardımcı fonksiyonlar vardır. Projedeki ana akışı anlamak için önce
`extract_pdf` fonksiyonuna bakmak yeterlidir.
"""

import argparse
import json
import re
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class PdfExtractionResult:
    """Katman 01'in dışarı verdiği standart sonuç yapısı."""

    file_name: str
    file_path: str
    page_count: int
    text: str
    extraction_ok: bool
    error: str = ""
    extractor: str = ""
    warnings: list[str] | None = None


@dataclass
class CMap:
    """PDF font kodlarını gerçek karakterlere çeviren küçük eşleme tablosu."""

    mapping: dict[int, str]
    code_bytes: int = 2


@dataclass
class TextChunk:
    """PDF içinde koordinatı olan küçük metin parçası."""

    y: float
    x: float
    text: str


# Dışarıdan kullanılan fonksiyonlar


def extract_pdf(path: str | Path) -> PdfExtractionResult:
    """PDF dosyasını okur ve standart Katman 01 çıktısı üretir.

    Bu fonksiyon hata fırlatmak yerine hatayı `PdfExtractionResult.error` alanında döndürür.
    Böylece sonraki katmanlar PDF okunamadığında da kontrollü davranabilir.
    """

    pdf_path = Path(path)

    warnings: list[str] = []

    try:
        text, page_count, extractor = _extract_with_available_reader(pdf_path, warnings)
        return PdfExtractionResult(
            file_name=pdf_path.name,
            file_path=str(pdf_path),
            page_count=page_count,
            text=text,
            extraction_ok=bool(text.strip()),
            extractor=extractor,
            warnings=warnings,
        )
    except Exception as exc:
        return PdfExtractionResult(
            file_name=pdf_path.name,
            file_path=str(pdf_path),
            page_count=0,
            text="",
            extraction_ok=False,
            error=f"{type(exc).__name__}: {exc}",
            extractor="none",
            warnings=warnings,
        )


def extract_pdf_text(path: str | Path) -> str:
    """Sonraki katmanlar için kısa yol: sadece metni döndürür."""

    return extract_pdf(path).text


# ---------------------------------------------------------------------------
# Ana PDF okuma akışı
# ---------------------------------------------------------------------------


def _extract_with_available_reader(path: Path, warnings: list[str]) -> tuple[str, int, str]:
    """Önce güçlü PDF okuyucuyu dener, olmazsa yerel okuyucuya düşer."""

    pymupdf_result = _extract_with_pymupdf(path, warnings)
    if pymupdf_result:
        text, page_count = pymupdf_result
        if text.strip():
            return text, page_count, "pymupdf"

        warnings.append("PyMuPDF belgeyi açtı ancak metin çıkaramadı; yerel okuyucu denendi.")

    text, page_count = _extract_text_and_page_count(path)
    extractor = "builtin"

    if not text.strip():
        warnings.append("PDF içinden metin çıkarılamadı. Belge taranmış veya görsel tabanlı olabilir.")

    return text, page_count, extractor


def _extract_with_pymupdf(path: Path, warnings: list[str]) -> tuple[str, int] | None:
    """PyMuPDF kuruluysa PDF metnini onunla çıkarır."""

    try:
        import fitz
    except ImportError:
        return None

    try:
        with fitz.open(path) as document:
            page_texts = [page.get_text("text").strip() for page in document]
            text = "\n\n".join(page_text for page_text in page_texts if page_text)
            return text.strip(), document.page_count
    except Exception as exc:
        warnings.append(f"PyMuPDF okuma hatası: {type(exc).__name__}: {exc}")
        return None


def _extract_text_and_page_count(path: Path) -> tuple[str, int]:
    """PDF içeriğini çözer, sayfalardaki metinleri birleştirir."""

    pdf_bytes = path.read_bytes()

    # PDF dosyaları "object" denen küçük parçalardan oluşur.
    pdf_objects = _parse_pdf_objects(pdf_bytes)

    # PDF içinde bazı fontlar harfleri doğrudan A/B/C diye saklamaz.
    # ToUnicode CMap bilgisi bu font kodlarını gerçek karakterlere çevirmemizi sağlar.
    font_cmaps = _load_font_cmaps(pdf_objects)

    pages = _find_pages(pdf_objects)
    page_texts: list[str] = []

    for page in pages:
        page_text = _extract_text_from_page(page, pdf_objects, font_cmaps)
        if page_text.strip():
            page_texts.append(page_text)

    return "\n\n".join(page_texts).strip(), len(pages)


def _extract_text_from_page(
    page: bytes,
    pdf_objects: dict[int, bytes],
    font_cmaps: dict[int, CMap],
) -> str:
    """Tek bir PDF sayfasındaki metin parçalarını çıkarır."""

    resource_ref = _reference_number(page, b"Resources")
    content_refs = _content_references(page)

    # Bazı PDF'lerde Resources ayrı object olarak durur, bazılarında sayfanın içindedir.
    resource_object = pdf_objects.get(resource_ref, page)
    page_fonts = _page_font_cmaps(resource_object, font_cmaps)

    chunks: list[TextChunk] = []
    for content_ref in content_refs:
        content_object = pdf_objects.get(content_ref, b"")
        content_stream = _stream_data(content_object)
        chunks.extend(_extract_text_chunks(content_stream, page_fonts))

    return _chunks_to_readable_text(chunks)


# ---------------------------------------------------------------------------
# PDF object ve stream yardımcıları
# ---------------------------------------------------------------------------


def _parse_pdf_objects(pdf_bytes: bytes) -> dict[int, bytes]:
    """PDF içindeki `12 0 obj ... endobj` bloklarını ayırır."""

    return {
        int(match.group(1)): match.group(2)
        for match in re.finditer(rb"(\d+)\s+0\s+obj\s*(.*?)\s*endobj", pdf_bytes, re.S)
    }


def _stream_data(pdf_object: bytes) -> bytes:
    """PDF object içindeki stream verisini döndürür.

    PDF stream'leri sıkıştırılmış olabilir. `/FlateDecode` gördüğümüzde `zlib` ile açıyoruz.
    """

    match = re.search(rb"stream\r?\n(.*?)\r?\nendstream", pdf_object, re.S)
    if not match:
        return b""

    data = match.group(1)
    if b"/FlateDecode" not in pdf_object:
        return data.strip(b"\r\n")

    for candidate in (data, data.strip(b"\r\n"), data.strip()):
        try:
            return zlib.decompress(candidate)
        except zlib.error:
            continue

    return b""


def _find_pages(pdf_objects: dict[int, bytes]) -> list[bytes]:
    """PDF içindeki gerçek sayfa object'lerini bulur."""

    pages: list[tuple[int, bytes]] = []
    for object_no, pdf_object in pdf_objects.items():
        is_page = b"/Type /Page" in pdf_object
        is_pages_container = b"/Type /Pages" in pdf_object
        if is_page and not is_pages_container:
            pages.append((object_no, pdf_object))

    return [page for _, page in sorted(pages)]


def _reference_number(pdf_object: bytes, key: bytes) -> int:
    """`/Resources 13 0 R` gibi bir referanstaki object numarasını döndürür."""

    match = re.search(rb"/" + key + rb"\s+(\d+)\s+0\s+R", pdf_object)
    return int(match.group(1)) if match else -1


def _content_references(page_object: bytes) -> list[int]:
    """Sayfanın metin/çizim içeriğini taşıyan content object numaralarını bulur."""

    array_match = re.search(rb"/Contents\s*\[(.*?)\]", page_object, re.S)
    if array_match:
        return [int(ref) for ref in re.findall(rb"(\d+)\s+0\s+R", array_match.group(1))]

    single = _reference_number(page_object, b"Contents")
    return [single] if single > 0 else []


# ---------------------------------------------------------------------------
# Font kodu -> gerçek karakter dönüşümü
# ---------------------------------------------------------------------------


def _load_font_cmaps(pdf_objects: dict[int, bytes]) -> dict[int, CMap]:
    """PDF font object'lerinden ToUnicode CMap bilgilerini toplar."""

    font_cmaps: dict[int, CMap] = {}

    for object_no, pdf_object in pdf_objects.items():
        match = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", pdf_object)
        if not match:
            continue

        cmap_ref = int(match.group(1))
        cmap_object = pdf_objects.get(cmap_ref, b"")
        cmap_text = _stream_data(cmap_object).decode("latin1", errors="ignore")
        font_cmaps[object_no] = _parse_cmap(cmap_text)

    return font_cmaps


def _parse_cmap(cmap_text: str) -> CMap:
    """ToUnicode CMap metnini Python sözlüğüne çevirir."""

    mapping: dict[int, str] = {}
    source_hex_lengths: list[int] = []
    mode: str | None = None

    for raw_line in cmap_text.splitlines():
        line = raw_line.strip()

        if "beginbfchar" in line:
            mode = "bfchar"
            continue
        if "endbfchar" in line:
            mode = None
            continue
        if "beginbfrange" in line:
            mode = "bfrange"
            continue
        if "endbfrange" in line:
            mode = None
            continue
        if not mode:
            continue

        if mode == "bfchar":
            _read_single_cmap_mapping(line, mapping, source_hex_lengths)
        elif mode == "bfrange":
            _read_cmap_range(line, mapping, source_hex_lengths)

    code_bytes = max(1, max(source_hex_lengths or [4]) // 2)
    return CMap(mapping=mapping, code_bytes=code_bytes)


def _read_single_cmap_mapping(
    line: str,
    mapping: dict[int, str],
    source_hex_lengths: list[int],
) -> None:
    """CMap içindeki tek karakter eşlemesini okur."""

    match = re.match(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", line)
    if not match:
        return

    source_hex, target_hex = match.groups()
    source_hex_lengths.append(len(source_hex))
    mapping[int(source_hex, 16)] = _unicode_from_hex(target_hex)


def _read_cmap_range(
    line: str,
    mapping: dict[int, str],
    source_hex_lengths: list[int],
) -> None:
    """CMap içindeki aralık eşlemelerini okur."""

    array_match = re.match(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*)\]", line)
    if array_match:
        start_hex, _, values_text = array_match.groups()
        start = int(start_hex, 16)
        source_hex_lengths.append(len(start_hex))
        values = re.findall(r"<([0-9A-Fa-f]+)>", values_text)
        for offset, target_hex in enumerate(values):
            mapping[start + offset] = _unicode_from_hex(target_hex)
        return

    direct_match = re.match(
        r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>",
        line,
    )
    if not direct_match:
        return

    start_hex, end_hex, target_hex = direct_match.groups()
    start = int(start_hex, 16)
    end = int(end_hex, 16)
    target = int(target_hex, 16)
    source_hex_lengths.append(len(start_hex))

    for code in range(start, end + 1):
        mapping[code] = chr(target + code - start)


def _unicode_from_hex(hex_text: str) -> str:
    """`0041` gibi hex Unicode değerini gerçek karaktere çevirir."""

    if len(hex_text) % 4:
        return bytes.fromhex(hex_text).decode("latin1", errors="replace")

    return "".join(chr(int(hex_text[i : i + 4], 16)) for i in range(0, len(hex_text), 4))


def _page_font_cmaps(resource_object: bytes, font_cmaps: dict[int, CMap]) -> dict[str, CMap]:
    """Sayfadaki font adlarını ilgili CMap ile eşleştirir."""

    page_fonts: dict[str, CMap] = {}
    font_dict = re.search(rb"/Font\s*<<(.*?)>>", resource_object, re.S)
    source = font_dict.group(1) if font_dict else resource_object

    for font_name, object_no in re.findall(rb"/([A-Za-z0-9]+)\s+(\d+)\s+0\s+R", source):
        cmap = font_cmaps.get(int(object_no))
        if cmap:
            page_fonts[font_name.decode("ascii", errors="ignore")] = cmap

    return page_fonts


# ---------------------------------------------------------------------------
# Sayfa içindeki metin parçalarını okuma
# ---------------------------------------------------------------------------


def _extract_text_chunks(content_stream: bytes, page_fonts: dict[str, CMap]) -> list[TextChunk]:
    """Sayfa stream'i içindeki metin bloklarını koordinatlarıyla çıkarır."""

    chunks: list[TextChunk] = []

    # PDF'de metin blokları genelde BT ... ET arasında bulunur.
    for block_match in re.finditer(rb"BT\s+(.*?)\s+ET", content_stream, re.S):
        block = block_match.group(1)
        x, y = _text_position(block)
        font_name = _text_font_name(block)
        cmap = page_fonts.get(font_name)

        text = _decode_text_operators(block, cmap)
        text = _clean_text(text)

        if text:
            chunks.append(TextChunk(y=y, x=x, text=text))

    return chunks


def _text_position(text_block: bytes) -> tuple[float, float]:
    """Metin bloğunun PDF sayfasındaki yaklaşık x/y koordinatını bulur."""

    match = re.search(
        rb"[-+]?\d*\.?\d+\s+[-+]?\d*\.?\d+\s+[-+]?\d*\.?\d+\s+[-+]?\d*\.?\d+\s+([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)\s+Tm",
        text_block,
    )
    if not match:
        return 0.0, 0.0
    return float(match.group(1)), float(match.group(2))


def _text_font_name(text_block: bytes) -> str:
    """Metin bloğunda kullanılan font adını bulur."""

    match = re.search(rb"/([A-Za-z0-9]+)\s+[-+]?\d*\.?\d+\s+Tf", text_block)
    return match.group(1).decode("ascii", errors="ignore") if match else ""


def _decode_text_operators(text_block: bytes, cmap: CMap | None) -> str:
    """PDF metin operatörlerini okuyup ham metne çevirir."""

    text_parts: list[str] = []
    text_operator_pattern = rb"(\[(?:.|\n)*?\]\s*TJ|<[^>]+>\s*Tj|\((?:\\.|[^\\)])*\)\s*Tj)"

    for match in re.finditer(text_operator_pattern, text_block, re.S):
        operator = match.group(1)
        expression = operator[:-2]  # sondaki Tj/TJ kısmını çıkarıyoruz
        text_parts.append(_decode_text_expression(expression, cmap))

    return "".join(text_parts)


def _decode_text_expression(expression: bytes, cmap: CMap | None) -> str:
    """PDF metin ifadesindeki literal ve hex string parçalarını çözer."""

    output: list[str] = []
    i = 0

    while i < len(expression):
        current = expression[i : i + 1]

        if current == b"(":
            end = _find_literal_end(expression, i + 1)
            output.append(_decode_literal(expression[i + 1 : end], cmap))
            i = end + 1
            continue

        if current == b"<" and expression[i + 1 : i + 2] != b"<":
            end = expression.find(b">", i + 1)
            if end < 0:
                break
            output.append(_decode_hex_string(expression[i + 1 : end], cmap))
            i = end + 1
            continue

        i += 1

    return "".join(output)


def _find_literal_end(data: bytes, start: int) -> int:
    """Parantez içindeki PDF literal string'in nerede bittiğini bulur."""

    depth = 1
    escaped = False

    for i in range(start, len(data)):
        byte = data[i]
        if escaped:
            escaped = False
        elif byte == 92:  # ters slash
            escaped = True
        elif byte == 40:  # (
            depth += 1
        elif byte == 41:  # )
            depth -= 1
            if depth == 0:
                return i

    return len(data)


def _decode_literal(value: bytes, cmap: CMap | None) -> str:
    """PDF literal string'i normal metne çevirir."""

    raw = _unescape_pdf_literal(value)
    if not cmap:
        return raw.decode("latin1", errors="replace")
    return _decode_bytes_with_cmap(raw, cmap)


def _unescape_pdf_literal(value: bytes) -> bytes:
    """PDF literal string içindeki kaçış karakterlerini çözer."""

    output = bytearray()
    i = 0

    while i < len(value):
        byte = value[i]
        if byte != 92 or i + 1 >= len(value):
            output.append(byte)
            i += 1
            continue

        next_byte = value[i + 1]
        simple_escapes = {
            ord("n"): b"\n",
            ord("r"): b"\r",
            ord("t"): b"\t",
            ord("b"): b"\b",
            ord("f"): b"\f",
        }

        if next_byte in simple_escapes:
            output.extend(simple_escapes[next_byte])
            i += 2
        elif next_byte in b"()\\":
            output.append(next_byte)
            i += 2
        elif 48 <= next_byte <= 55:
            i = _append_octal_escape(value, i + 1, output)
        else:
            output.append(next_byte)
            i += 2

    return bytes(output)


def _append_octal_escape(value: bytes, start: int, output: bytearray) -> int:
    """PDF içindeki üç basamağa kadar octal kaçış değerini çözer."""

    i = start
    digits = bytearray()

    while i < len(value) and len(digits) < 3 and 48 <= value[i] <= 55:
        digits.append(value[i])
        i += 1

    output.append(int(bytes(digits), 8))
    return i


def _decode_hex_string(value: bytes, cmap: CMap | None) -> str:
    """PDF hex string'i normal metne çevirir."""

    cleaned = re.sub(rb"\s+", b"", value)
    if len(cleaned) % 2:
        cleaned += b"0"

    try:
        raw = bytes.fromhex(cleaned.decode("ascii"))
    except ValueError:
        return ""

    if not cmap:
        return raw.decode("latin1", errors="replace")
    return _decode_bytes_with_cmap(raw, cmap)


def _decode_bytes_with_cmap(raw: bytes, cmap: CMap) -> str:
    """Font kodlarını CMap yardımıyla gerçek karakterlere çevirir."""

    chars: list[str] = []
    step = cmap.code_bytes

    for i in range(0, len(raw), step):
        code_bytes = raw[i : i + step]
        if len(code_bytes) < step:
            continue
        code = int.from_bytes(code_bytes, "big")
        chars.append(cmap.mapping.get(code, ""))

    return "".join(chars)


def _chunks_to_readable_text(chunks: list[TextChunk]) -> str:
    """Koordinatlı metin parçalarını yaklaşık okuma sırasına dizer."""

    if not chunks:
        return ""

    grouped_lines = _group_chunks_by_line(chunks)
    output: list[str] = []

    for line in grouped_lines:
        ordered_line = sorted(line, key=lambda chunk: chunk.x)
        line_text = " ".join(chunk.text for chunk in ordered_line)
        line_text = _clean_text(line_text)
        if line_text:
            output.append(line_text)

    return "\n".join(output)


def _group_chunks_by_line(chunks: list[TextChunk]) -> list[list[TextChunk]]:
    """Yakın y koordinatına sahip parçaları aynı satır kabul eder."""

    lines: list[list[TextChunk]] = []

    for chunk in sorted(chunks, key=lambda item: (-item.y, item.x)):
        target_line = _find_matching_line(lines, chunk)
        if target_line is None:
            lines.append([chunk])
        else:
            target_line.append(chunk)

    return lines


def _find_matching_line(lines: list[list[TextChunk]], chunk: TextChunk) -> list[TextChunk] | None:
    """Verilen metin parçasının mevcut satırlardan birine ait olup olmadığını bulur."""

    for line in lines:
        if abs(line[0].y - chunk.y) < 3:
            return line
    return None


def _clean_text(text: str) -> str:
    """Metindeki gereksiz boşlukları ve null karakterlerini temizler."""

    text = text.replace("\x00", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Terminalden tek başına çalıştırma
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Katman 01 - PDF okuma")
    parser.add_argument("pdf", help="Metni çıkarılacak PDF dosyası")
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=1200,
        help="Ekrana basılacak metin önizleme uzunluğu",
    )
    args = parser.parse_args()

    result = extract_pdf(args.pdf)
    payload = asdict(result)

    if args.preview_chars >= 0:
        payload["text_preview"] = payload["text"][: args.preview_chars]
        payload["text_length"] = len(payload["text"])
        del payload["text"]

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
