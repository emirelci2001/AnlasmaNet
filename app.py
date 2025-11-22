import os
import io
import re
import json
import pdfplumber
import streamlit as st
from typing import List, Tuple, Dict, Any
import requests
import urllib.parse

@st.cache_data(show_spinner=False)
def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_parts: List[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t.strip():
                text_parts.append(t)
    return "\n\n".join(text_parts).strip()

def _config_dir() -> str:
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "AnlasmaNet")

def _config_path() -> str:
    return os.path.join(_config_dir(), "config.json")

def load_saved_api_key() -> str:
    try:
        p = _config_path()
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                k = data.get("GOOGLE_API_KEY", "")
                return k.strip()
    except Exception:
        return ""
    return ""

def save_api_key(key: str) -> bool:
    try:
        os.makedirs(_config_dir(), exist_ok=True)
        data = {}
        p = _config_path()
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as rf:
                    data = json.load(rf)
            except Exception:
                data = {}
        data["GOOGLE_API_KEY"] = key.strip()
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True
    except Exception:
        return False

def delete_api_key() -> bool:
    try:
        p = _config_path()
        if os.path.exists(p):
            os.remove(p)
        return True
    except Exception:
        return False

def save_settings(model: str, audience: str) -> bool:
    try:
        os.makedirs(_config_dir(), exist_ok=True)
        data = {}
        p = _config_path()
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as rf:
                    data = json.load(rf)
            except Exception:
                data = {}
        data["MODEL"] = model
        data["AUDIENCE"] = audience
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True
    except Exception:
        return False

def load_settings() -> Dict[str, str]:
    try:
        p = _config_path()
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
                return {"MODEL": d.get("MODEL", "gemini-1.5-flash"), "AUDIENCE": d.get("AUDIENCE", "Avukat")}
    except Exception:
        return {"MODEL": "gemini-1.5-flash", "AUDIENCE": "Avukat"}
    return {"MODEL": "gemini-1.5-flash", "AUDIENCE": "Avukat"}

SAMPLE_CONTRACTS: List[Tuple[str, str]] = [
    ("Yok", ""),
    ("Hizmet Sözleşmesi (Temel)", "Taraflar arasında hizmet sağlanacaktır. Gizlilik süresizdir. Cezai şart ödemelerde gecikme halinde %50 uygulanır. Yetkili mahkeme karşı tarafın bulunduğu yerdir. Revizyonlar sınırsızdır. Ödeme süresi 60 gündür."),
    ("Pazarlama İşbirliği", "Influencer, marka için içerik üretir. Kullanım hakkı sınırsız ve süresiz devredilir. Fesih tek taraflıdır. Gecikme faizi yüksek olabilir. Gizlilik maddesi belirsizdir."),
]

def build_system_prompt(audience: str = "Freelancer") -> str:
    if audience == "Avukat":
        return (
            "Rol: Türk Ticaret ve Borçlar Hukuku odaklı sözleşme analisti.\n"
            "Hedef Kitle: Uygulama deneyimi olan avukatlar.\n"
            "Dil ve Stil: Resmi, analitik, kısa ve net. Gerekli yerlerde teknik terim kullanılabilir; belirsiz ifadeler işaretlenir.\n"
            "Sınırlar: Bilgilendirme amaçlı analiz; somut olay danışmanlığı değildir.\n\n"
            "Görevler:\n"
            "1) Tespit: Cezai şart, fesih, gizlilik/rekabet, yetkili mahkeme/tahkim, telif/kullanım, sorumluluk ve ödeme vadeleri.\n"
            "2) Puanlama: 10 üzerinden Güven Puanı ve kısaltılmış gerekçe.\n"
            "3) Özet: Madde/satır düzeyinde risk ve öneri.\n"
            "4) Redline: Kısa, uygulanabilir değişiklik önerileri.\n\n"
            "Çıktı Formatı (Markdown):\n"
            "## 🛡️ Güven Puanı: X/10\n"
            "### 🚨 Kırmızı Bayraklar (Riskler)\n"
            "- **Madde No:** [Riskli Özeti] -> [Öneri]\n"
            "### ✅ Olumlu Yanlar\n"
            "- [Olumlu maddeler]\n"
            "### 📝 Sonuç Özeti\n"
            "[Genel değerlendirme]\n"
        )
    else:
        return (
            "Rol: Uzman Türk Ticaret ve Borçlar Hukuku odaklı sözleşme analisti.\n"
            "Hedef Kitle: Hukuk eğitimi olmayan freelancerlar, ajans sahipleri, influencerlar ve küçük işletmeler.\n"
            "Dil ve Stil: Basit, öğretici, net Türkçe. Hukuk jargonu kullanma; gerektiğinde terimleri günlük dile çevirerek açıkla.\n"
            "Sınırlar: Bilgilendirme amaçlı analiz sun. Kesin hukuki mütalaa yerine pratik risk ve müzakere tavsiyesi ver.\n\n"
            "Görevler:\n"
            "1) Tespit: Sözleşmede kullanıcı aleyhine olabilecek maddeleri bul (ör. cezai şart, tek taraflı fesih, süresiz gizlilik/rekabet yasağı, yetkili mahkeme ve tahkim, telif ve kullanım devri, sorumluluk sınırlaması/üst sınırı yok, gecikme faizi aşırı, revizyon/teslim kabulleri tek taraflı, alt yüklenici yasağı, veri koruma/KVKK, ifa ve kabul süreçleri, iptal koşulları, ceza/teminatlar).\n"
            "2) Puanlama: 10 üzerinden Güven Puanı ver. 10: çok güvenli, 1: çok riskli. Puanı gerekçelendir.\n"
            "3) Sadeleştirme: Riskli maddeleri lise öğrencisinin anlayacağı günlük Türkçe ile özetle. Jargon kullanma; terimleri kısa açıklamalarla sadeleştir.\n"
            "4) Tavsiye: Her risk için karşı taraftan istenebilecek net, kısa, uygulanabilir düzeltme cümleleri yaz.\n\n"
            "Risk Puanlama Çerçevesi:\n"
            "- Başlangıç puanı: 10. Yüksek etki: -2/-3, orta: -1/-2, düşük: -0.5/-1.\n"
            "- Renk: 8–10 Yeşil; 5–7 Sarı; 1–4 Kırmızı.\n\n"
            "Çıktı Formatı (Markdown):\n"
            "## 🛡️ Güven Puanı: X/10\n"
            "### 🚨 Kırmızı Bayraklar (Riskler)\n"
            "- **Madde No:** [Riskli Madde Özeti] -> [Yorum ve Tavsiye]\n"
            "### ✅ Olumlu Yanlar\n"
            "- [Olumlu maddeler]\n"
            "### 📝 Sonuç Özeti\n"
            "[Genel görüş]\n"
        )

RISK_KEYWORDS: List[Tuple[str, int, str]] = [
    ("tek taraflı fesih", 3, "Fesih iki tarafa eşitlensin ve bildirim süresi eklensin."),
    ("cezai şart", 3, "Cezai şart kaldırılsın ya da toplam ücretin %10’u ile sınırlandırılsın."),
    ("süresiz gizlilik", 2, "Gizlilik süresi 6–12 ay ile sınırlandırılsın."),
    ("rekabet yasağı", 2, "Rekabet yasağı kaldırılmalı veya en fazla 6 ay ve konu/saha ile sınırlı."),
    ("yetkili mahkeme", 2, "Yetkili mahkeme tarafların bulunduğu yer olarak dengelensin."),
    ("tahkim", 2, "Tahkim zorunluysa masraf paylaşımı ve yerel erişim sağlansın."),
    ("sorumluluk sınırsız", 3, "Sorumluluk toplam sözleşme ücreti ile sınırlandırılsın."),
    ("gizlilik", 1, "Gizlilik kapsamı sınırlı ve süreli olsun, ticari sır tanımı netleşsin."),
    ("gecikme faizi", 2, "Gecikme faizi makul bir üst sınırla sınırlandırılsın."),
    ("teslim", 1, "Teslim ve kabul kriterleri ölçülebilir ve iki taraflı yazılsın."),
    ("revizyon", 1, "Revizyon sayısı ve kapsamı netleşsin; ek işler ayrıca fiyatlandırılsın."),
    ("telif", 2, "Kullanım lisansı kapsamı ve süresi sınırlı, ödeme ile koşullu yazılsın."),
]

def _split_clauses(text: str) -> List[Tuple[str, str]]:
    lines = text.splitlines()
    clauses: List[Tuple[str, str]] = []
    current_id = "Genel"
    current_buf: List[str] = []
    for ln in lines:
        m = re.search(r"(?i)\bmadde\s*(\d+)\b", ln)
        if m:
            if current_buf:
                clauses.append((current_id, "\n".join(current_buf).strip()))
            current_id = f"Madde {m.group(1)}"
            current_buf = [ln]
        else:
            if ln.strip() == "" and current_buf:
                current_buf.append(ln)
            else:
                current_buf.append(ln)
    if current_buf:
        clauses.append((current_id, "\n".join(current_buf).strip()))
    if not clauses:
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        for i, p in enumerate(paras, 1):
            clauses.append((f"Bölüm {i}", p))
    return clauses

def _snippet(s: str, match: re.Match, span: int = 180) -> str:
    start = max(0, match.start() - span // 2)
    end = min(len(s), match.end() + span // 2)
    return s[start:end].replace("\n", " ").strip()

def _clause_spans(text: str) -> List[Dict[str, Any]]:
    spans: List[Dict[str, Any]] = []
    idx = [(m.group(1), m.start()) for m in re.finditer(r"(?i)\bmadde\s*(\d+)\b", text)]
    for i, (num, start) in enumerate(idx):
        end = idx[i+1][1] if i+1 < len(idx) else len(text)
        spans.append({"id": f"Madde {num}", "start": start, "end": end})
    return spans

ADV_PATTERNS: List[Dict[str, Any]] = [
    {"name": "Tek taraflı fesih", "pattern": r"(?i)tek tarafl[ıi].*fes(h|i)", "weight": 3, "suggest": "Fesih hakkını karşılıklı ve bildirim süreli yapalım."},
    {"name": "Cezai şart", "pattern": r"(?i)cezai\s*şart", "weight": 3, "suggest": "Cezai şart kaldırılmalı veya toplam ücretin %10’u ile sınırlandırılmalı."},
    {"name": "Süresiz gizlilik", "pattern": r"(?i)süresiz.*gizlilik|gizlilik.*süresiz", "weight": 2, "suggest": "Gizlilik süresi 6–12 ay ile sınırlandırılmalı."},
    {"name": "Rekabet yasağı", "pattern": r"(?i)rekabet\s*yasa[ğg][ıi]", "weight": 2, "suggest": "En fazla 6 ay, konu ve coğrafya ile sınırlı olmalı."},
    {"name": "Yetkili mahkeme", "pattern": r"(?i)yetkili\s*mahkeme|tahkim", "weight": 2, "suggest": "Yer seçimi dengeli olmalı; masraf paylaşımı netleşmeli."},
    {"name": "Sınırsız sorumluluk", "pattern": r"(?i)sorumluluk.*(sınırsız|her t[üu]rl[üu])", "weight": 3, "suggest": "Toplam sözleşme bedeli ile sınırlandırılmalı."},
    {"name": "Gecikme faizi", "pattern": r"(?i)gecikme\s*faizi", "weight": 2, "suggest": "Makul bir üst sınır ve gecikme gerekçesi tanımlanmalı."},
    {"name": "Sebep göstermeden iptal", "pattern": r"(?i)sebep\s*g[öo]stermeden.*(iptal|fes(h|i))", "weight": 2, "suggest": "İptal durumda makul tazminat/ödenen kısmın iadesi düzenlenmeli."},
    {"name": "Feragat", "pattern": r"(?i)peşin\s*feragat|feragat\s*edilir", "weight": 2, "suggest": "Genel feragat kaldırılmalı; hak arama özgürlüğü korunmalı."},
    {"name": "Telif ve kullanım devri", "pattern": r"(?i)telif|kullan[ıi]m\s*hakk[ıi]", "weight": 2, "suggest": "Lisans kapsamı/süresi sınırlı ve ödeme ile koşullu olmalı."},
    {"name": "Revizyon sınırı yok", "pattern": r"(?i)revizyon(?!.*\d+)|sınırsız\s*revizyon", "weight": 1, "suggest": "Revizyon sayısı ve kapsamı net yazılmalı."},
    {"name": "Teslim ve kabul belirsiz", "pattern": r"(?i)teslim.*(kabul|onay).*muğlak|kabul.*tek tarafl[ıi]", "weight": 1, "suggest": "Ölçülebilir kabul kriterleri ve iki taraflı süreç yazılmalı."},
]

def _duration_present(text: str) -> bool:
    return bool(re.search(r"(?i)(\d+)\s*(g[üu]n|hafta|ay|y[ıi]l)", text))

def _payment_risk(text: str) -> List[Dict[str, Any]]:
    items = []
    for m in re.finditer(r"(?i)(\d{2,})\s*g[üu]n", text):
        days = int(m.group(1))
        if days > 45:
            items.append({"name": "Uzun ödeme vadesi", "weight": 2 if days <= 60 else 3, "suggest": "Ödeme vadesi 15–30 gün aralığında olmalı.", "match": m})
    if re.search(r"(?i)ödeme.*(kabul|onay).*tek tarafl[ıi]", text):
        m = re.search(r"(?i)ödeme.*(kabul|onay).*tek tarafl[ıi]", text)
        if m:
            items.append({"name": "Ödeme tek taraflı kabule bağlı", "weight": 2, "suggest": "Ödeme objektif teslim koşullarına bağlanmalı ve iki taraflı olmalı.", "match": m})
    return items

def _positives(text: str) -> List[str]:
    pos = []
    if re.search(r"(?i)fes(h|i)h\s*hakk[ıi].*(iki|karşılıklı)\s*taraf", text):
        pos.append("Fesih hakkı karşılıklı düzenlenmiş.")
    if re.search(r"(?i)sorumluluk.*(üst\s*s[ıi]n[ıi]r|azami|limit).*?(bedel|tutar|miktar)", text):
        pos.append("Sorumluluk üst sınırla sınırlandırılmış.")
    if re.search(r"(?i)gizlilik.*(\d+)\s*(ay|y[ıi]l)", text):
        pos.append("Gizlilik süresi belirli ve süreli.")
    if re.search(r"(?i)revizyon.*?(en\s*fazla|en\s*çok|\d+)", text):
        pos.append("Revizyonlar sayı veya kapsam olarak sınırlandırılmış.")
    if re.search(r"(?i)ödeme.*(15|30)\s*g[üu]n", text):
        pos.append("Ödeme vadesi 15–30 gün aralığında.")
    if re.search(r"(?i)kabul\s*kriterleri|ölçülebilir\s*kriter", text):
        pos.append("Kabul kriterleri ölçülebilir şekilde yazılmış.")
    if re.search(r"(?i)yetkili\s*mahkeme.*(taraflar|bulunduğu\s*yer)", text):
        pos.append("Yetkili mahkeme seçimi dengeli.")
    if re.search(r"(?i)taraf(lar|ı)", text):
        pos.append("Taraflar açıkça belirtilmiş.")
    if re.search(r"(?i)(sözleşmenin|işin)\s*konusu|hizmet", text):
        pos.append("İşin/kapsamın tanımı mevcut.")
    if re.search(r"(?i)(başlangıç|bitiş|süre|tarih).*?(\d+)", text):
        pos.append("Tarih veya süre bilgisi yazılmış.")
    return pos

@st.cache_data(show_spinner=False)
def advanced_analyze(text: str, detailed: bool = True, total_fee: float = None, monthly_fee: float = None, audience: str = "Avukat") -> Dict[str, Any]:
    clauses = _split_clauses(text)
    spans = _clause_spans(text)
    total_score = 10
    risk_items: List[Dict[str, Any]] = []
    positives: List[str] = _positives(text)
    lowered = text.lower()
    for pat in ADV_PATTERNS:
        for m in re.finditer(pat["pattern"], text):
            total_score -= pat["weight"]
            clause = ""
            ms = m.start()
            for sp in spans:
                if ms >= sp["start"] and ms < sp["end"]:
                    clause = sp["id"]
                    break
            risk_items.append({"name": pat["name"], "weight": pat["weight"], "suggest": pat["suggest"], "match": m, "snippet": _snippet(text, m), "clause": clause})
    for pr in _payment_risk(text):
        total_score -= pr["weight"]
        clause = ""
        ms = pr["match"].start() if pr.get("match") else -1
        if ms >= 0:
            for sp in spans:
                if ms >= sp["start"] and ms < sp["end"]:
                    clause = sp["id"]
                    break
        risk_items.append({"name": pr["name"], "weight": pr["weight"], "suggest": pr["suggest"], "match": pr.get("match"), "snippet": _snippet(text, pr["match"]) if pr.get("match") else "", "clause": clause})
    if re.search(r"(?i)gizlilik", lowered) and not _duration_present(text):
        total_score -= 2
        risk_items.append({"name": "Gizlilik süresi belirtilmemiş", "weight": 2, "suggest": "Gizlilik süresi 6–12 ay ile sınırlandırılmalı.", "match": None, "snippet": ""})
    total_score = max(1, min(10, total_score))
    color = "Yeşil" if total_score >= 8 else ("Sarı" if total_score >= 5 else "Kırmızı")
    out: List[str] = []
    if audience == "Freelancer":
        out.append(f"## 🛡️ Güven Puanı: {total_score}/10 ({color})")
        out.append("### ⚠️ Önemli Riskler")
        if risk_items:
            for it in risk_items:
                line = f"- {it['name']}: {it['suggest']}"
                out.append(line)
        else:
            out.append("- Belirgin risk yok.")
        out.append("### ✅ İyi Taraflar")
        if positives:
            out.extend([f"- {p}" for p in positives])
        else:
            out.append("- Dengeli maddeler var.")
        out.append("### 👉 Ne Yapmalıyım?")
    else:
        out.append(f"## 🛡️ Güven Puanı: {total_score}/10 ({color})")
        out.append("### 🚨 Kırmızı Bayraklar (Riskler)")
        if risk_items:
            for it in risk_items:
                prefix = f"{it['clause']}: " if it.get("clause") else ""
                line = f"- **{prefix}{it['name']}:** {it['snippet']} -> {it['suggest']}"
                out.append(line)
        else:
            out.append("- Belirgin bir kırmızı bayrak tespit edilmedi.")
        out.append("### ✅ Olumlu Yanlar")
        if positives:
            out.extend([f"- {p}" for p in positives])
        else:
            out.append("- Dengeli maddeler bulunursa burada listelenir.")
    out.append("### 📝 Sonuç Özeti")
    high = sum(1 for i in risk_items if i["weight"] >= 3)
    mid = sum(1 for i in risk_items if i["weight"] == 2)
    low = sum(1 for i in risk_items if i["weight"] == 1)
    decision = "İmzalama, kapsamlı revizyon şart." if total_score <= 4 else ("Müzakere ederek revizyonlarla imzalanabilir." if total_score <= 7 else "Küçük revizyonlarla imzalanabilir.")
    main_risks = ", ".join([i["name"] for i in sorted(risk_items, key=lambda x: -x["weight"])[:3]]) or "Belirgin ağır risk yok"
    main_pos = ", ".join(positives[:3]) or "Belirgin olumlu denge yok"
    if audience == "Freelancer":
        out.append(f"Karar: {decision}")
        out.append(f"Ana riskler: {main_risks}.")
        out.append(f"Olumlu noktalar: {main_pos}.")
    else:
        out.append(f"Risk matrisi: yüksek={high}, orta={mid}, düşük={low}. Karar: {decision}")
        out.append(f"Ana riskler: {main_risks}.")
        out.append(f"Olumlu noktalar: {main_pos}.")
    top3 = []
    seen = set()
    for it in sorted(risk_items, key=lambda x: -x["weight"]):
        s = it["suggest"]
        if s not in seen:
            seen.add(s)
            top3.append(s)
        if len(top3) == 3:
            break
    if audience == "Freelancer":
        out.append("### ✅ İmzalamadan Önce 3 Düzeltme")
    else:
        out.append("### ✅ Öncelikli Revizyonlar (3 madde)")
    if top3:
        out.extend([f"- {s}" for s in top3])
    if audience == "Freelancer":
        out.append("### 🧭 Müzakere Planı")
    else:
        out.append("### 🧭 Müzakere Planı")
    unique_suggest = []
    for i in risk_items:
        if i["suggest"] not in unique_suggest:
            unique_suggest.append(i["suggest"])
    if unique_suggest:
        out.extend([f"- {s}" for s in unique_suggest])
    else:
        out.append("- Belirgin müzakere talebi yok.")
    ceza_pct = None
    m_pct = re.search(r"(?i)(%\s*(\d{1,3}))|y[üu]zde\s*(\d{1,3})", text)
    if m_pct:
        ceza_pct = int(m_pct.group(2) or m_pct.group(3))
    liab_unlimited = any(i["name"] == "Sınırsız sorumluluk" for i in risk_items)
    long_pay = [i for i in risk_items if i["name"] == "Uzun ödeme vadesi"]
    if ceza_pct or liab_unlimited or long_pay:
        out.append("### 💰 Finansal Etki Tahmini")
        fee_str = "belirtilmedi"
        if total_fee and total_fee > 0:
            fee_str = f"{int(total_fee)} TL"
        if any(i["name"] == "Cezai şart" for i in risk_items):
            if total_fee and ceza_pct:
                out.append(f"- Olası ceza: yaklaşık {int(total_fee * ceza_pct/100)} TL (%{ceza_pct} oranıyla).")
            elif ceza_pct:
                out.append(f"- Olası ceza: %{ceza_pct} (toplam ücret {fee_str}).")
            else:
                out.append(f"- Olası ceza: toplam ücretin ~%10’u (toplam ücret {fee_str}).")
        if liab_unlimited:
            out.append("- Sorumluluk: sınırsız maruziyet. Öneri: toplam sözleşme bedeli ile sınırlandırılsın.")
        if long_pay:
            for lp in long_pay:
                if lp.get("match"):
                    days = int(re.search(r"(\d{2,})", text[lp["match"].start():lp["match"].end()]).group(1)) if re.search(r"(\d{2,})", text[lp["match"].start():lp["match"].end()]) else None
                    if days:
                        out.append(f"- Nakit akışı gecikmesi: {days} gün vade. Öneri: 15–30 gün.")
    if audience == "Freelancer":
        out.append("### ✍️ Karşı Tarafa Söyle")
        for s in unique_suggest:
            out.append(f"- {s}")
        out.append("### 📚 İyi Pratikler")
        out.append("- Cezai şart oranı ve üst sınırı yazılsın.")
        out.append("- Gizlilik ve rekabet yasağı süreli ve sınırlı olsun.")
        out.append("- Sorumluluk toplam bedelle sınırlandırılsın.")
        out.append("- Ödeme vadesi 15–30 gün olsun.")
        out.append("- Fesih karşılıklı ve bildirim süreli olsun.")
    else:
        out.append("### ✍️ Redline Cümleleri")
        for s in unique_suggest:
            out.append(f"- Önerilen ifade: {s}")
        out.append("### 📚 İyi Pratikler")
        out.append("- Cezai şart varsa oran ve üst sınır yazılsın.")
        out.append("- Gizlilik ve rekabet yasağı süreli ve konu/saha ile sınırlı olsun.")
        out.append("- Sorumluluk toplam bedel ile sınırlandırılsın; dolaylı zararlar hariç.")
        out.append("- Ödeme vadeleri 15–30 gün; kabul kriterleri ölçülebilir olsun.")
        out.append("- Fesih karşılıklı ve bildirim süreli düzenlensin.")
    return {
        "markdown": "\n".join(out),
        "score": total_score,
        "high": high,
        "mid": mid,
        "low": low,
        "suggestions": unique_suggest,
        "risks": [{"name": r["name"], "snippet": r["snippet"], "suggest": r["suggest"], "weight": r["weight"], "clause": r.get("clause", "")} for r in risk_items],
        "audience": audience
    }

def llm_analyze_gemini(text: str, total_fee: float = None, monthly_fee: float = None, api_key_override: str = "", model_name: str = "gemini-1.5-flash", chunk_size: int = 8000, audience: str = "Avukat") -> str:
    api_key = (api_key_override or os.getenv("GOOGLE_API_KEY", "")).strip()
    if not api_key:
        return advanced_analyze(text, detailed=True, audience=audience)["markdown"]
    try:
        params = {"key": api_key}
        list_url = "https://generativelanguage.googleapis.com/v1beta/models"
        avail_models = []
        try:
            lm = requests.get(list_url, params=params, timeout=30)
            if lm.status_code == 200:
                jd = lm.json()
                for m in jd.get("models", []):
                    name = m.get("name", "")
                    if name:
                        avail_models.append(name.split("/")[-1])
        except Exception:
            pass
        use_model = model_name
        if avail_models and use_model not in avail_models:
            alt = use_model + "-latest" if not use_model.endswith("-latest") else use_model
            if alt in avail_models:
                use_model = alt
        def call_once(t: str) -> str:
            payload = {
                "systemInstruction": {"role": "system", "parts": [{"text": build_system_prompt(audience)}]},
                "contents": [{"role": "user", "parts": [{"text": "Sözleşme Metni:\n" + t}]}],
                "generationConfig": {"temperature": 0.2}
            }
            url1 = f"https://generativelanguage.googleapis.com/v1beta/models/{use_model}:generateContent"
            r = requests.post(url1, params=params, json=payload, timeout=60)
            if r.status_code == 404:
                url2 = f"https://generativelanguage.googleapis.com/v1beta2/models/{use_model}:generateContent"
                r = requests.post(url2, params=params, json=payload, timeout=60)
            if r.status_code != 200:
                return f"### ℹ️ Gemini hata kodu: {r.status_code}\n"
            data = r.json()
            cands = data.get("candidates", [])
            if not cands:
                return ""
            parts = cands[0].get("content", {}).get("parts", [])
            return "".join([p.get("text", "") for p in parts]).strip()
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)] if len(text) > chunk_size else [text]
        outputs = [call_once(c) for c in chunks]
        dedup = []
        for o in outputs:
            if o and o not in dedup:
                dedup.append(o)
        base = "\n\n".join(dedup)
        enrich = advanced_analyze(text, detailed=True, total_fee=total_fee, monthly_fee=monthly_fee, audience=audience)
        return (base + "\n\n" + enrich["markdown"]) if base else enrich["markdown"]
    except Exception:
        return advanced_analyze(text, detailed=True, total_fee=total_fee, monthly_fee=monthly_fee, audience=audience)

st.set_page_config(page_title="AnlaşmaNet Beta", page_icon="🛡️", layout="centered")
st.title("AnlaşmaNet • Sözleşme Risk Analizi (Beta)")
st.caption("PDF yükle veya metni yapıştır, 1 dakikada özet ve tavsiye al.")
st.markdown("""
<style>
html, body { font-family: 'Segoe UI', Inter, Arial, sans-serif; }
h1,h2,h3 { margin: 0.5rem 0 0.3rem; }
.score { font-weight: 600; }
header { visibility: hidden; height: 0; }
footer { visibility: hidden; }
.stApp [data-testid="stToolbar"] { display: none; }
</style>
""", unsafe_allow_html=True)

uploaded = st.file_uploader("PDF yükle", type=["pdf"], key="upl_pdf")
text_input = st.text_area("Metni buraya yapıştır", height=200, key="txt_input")
saved_key = load_saved_api_key()
saved_settings = load_settings()
model_name = saved_settings.get("MODEL", "gemini-1.5-flash")
with st.sidebar:
    st.header("Ayarlar")
    audience = st.selectbox("Hedef Kitle", ["Avukat", "Freelancer"], index=0 if saved_settings.get("AUDIENCE") == "Avukat" else 1)
    demo_name = st.selectbox("Demo Sözleşme", [n for n, _ in SAMPLE_CONTRACTS], index=0)
    if st.button("Formu Sıfırla", key="btn_reset"):
        st.session_state["txt_input"] = ""
        st.session_state["upl_pdf"] = None
        st.experimental_rerun()
    

if st.button("Analiz Et", key="btn_analyze"):
    contract_text = ""
    if uploaded is not None:
        try:
            contract_text = extract_text_from_pdf(uploaded.read())
        except Exception as e:
            st.error("PDF metni çıkarılamadı. Metni yapıştırmayı deneyin.")
    if not contract_text and text_input.strip():
        contract_text = text_input.strip()
    if not contract_text and demo_name != "Yok":
        for n, t in SAMPLE_CONTRACTS:
            if n == demo_name:
                contract_text = t
                break
    if not contract_text:
        st.warning("Analiz için PDF veya metin sağlayın.")
    else:
        with st.spinner("Analiz yapılıyor..."):
            effective_key = saved_key or os.getenv("GOOGLE_API_KEY", "")
            if effective_key:
                report = llm_analyze_gemini(contract_text, api_key_override=effective_key, model_name=model_name, audience=audience)
            else:
                res = advanced_analyze(contract_text, detailed=True, audience=audience)
                report = res["markdown"]
        st.markdown(report)
        st.caption("Bu analiz bilgilendirme amacı taşır; hukuki danışmanlık değildir.")
        try:
            res2 = advanced_analyze(contract_text, detailed=True, audience=audience)
            st.metric("Güven Puanı", res2["score"]) 
            export_json = json.dumps(res2, ensure_ascii=False, indent=2)
            st.download_button("JSON indir", data=export_json, file_name="anlasmanet_rapor.json")
            rows = [["clause","name","weight","suggest","snippet"]] + [[r.get("clause",""), r["name"], r["weight"], r["suggest"], r["snippet"].replace("\n"," ")] for r in res2.get("risks", [])]
            csv_data = "\n".join([",".join([str(x).replace(",",";") for x in row]) for row in rows])
            st.download_button("CSV indir", data=csv_data, file_name="anlasmanet_riskler.csv", mime="text/csv")
            redline_txt = "\n".join([f"- {s}" for s in res2.get("suggestions", [])]) or "Öneri bulunamadı."
            email_body = (
                "Merhaba,\n\nSözleşme taslağı ile ilgili aşağıdaki revizyonları rica ederim:\n" +
                "\n".join([f"• {s}" for s in res2.get("suggestions", [])]) +
                ("\n\nTeşekkürler."))
            st.download_button("Redline Paketini indir (.txt)", data=redline_txt, file_name="redline.txt")
            st.download_button("Karşı tarafa e‑posta (.txt)", data=email_body, file_name="email_talep.txt")
            subject = urllib.parse.quote("Sözleşme revizyon talebi")
            body_q = urllib.parse.quote(email_body)
            st.markdown(f"[E‑posta oluştur](mailto:?subject={subject}&body={body_q})")
            try:
                os.makedirs(_config_dir(), exist_ok=True)
                with open(os.path.join(_config_dir(), "last_report.md"), "w", encoding="utf-8") as f:
                    f.write(report)
            except Exception:
                pass
            html_report = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>AnlaşmaNet Raporu</title><style>body{{font-family:Segoe UI,Inter,Arial,sans-serif;line-height:1.6;color:#1b1b1b}} h1,h2,h3{{margin:0.6rem 0}} .score{{font-weight:600}} .footer{{margin-top:24px;font-size:12px;color:#555}}</style></head><body><h1>AnlaşmaNet Raporu</h1><div class='score'>Güven Puanı: {res2['score']}/10</div><hr/><pre>{report}</pre><div class='footer'>Bu analiz bilgilendirme amacı taşır; hukuki danışmanlık değildir.</div></body></html>"
        st.download_button("HTML indir", data=html_report, file_name="anlasmanet_rapor.html", mime="text/html")
        except Exception:
            pass
        st.download_button("Raporu indir (.md)", data=report, file_name="anlasmanet_rapor.md")