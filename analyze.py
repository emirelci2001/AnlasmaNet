import re
from typing import List, Tuple, Dict, Any

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
                out.append(f"- {it['name']}: {it['suggest']}")
        else:
            out.append("- Belirgin risk yok.")
        out.append("### ✅ İyi Taraflar")
        if positives:
            out.extend([f"- {p}" for p in positives])
        else:
            out.append("- Dengeli maddeler var.")
    else:
        out.append(f"## 🛡️ Güven Puanı: {total_score}/10 ({color})")
        out.append("### 🚨 Kırmızı Bayraklar (Riskler)")
        if risk_items:
            for it in risk_items:
                prefix = f"{it['clause']}: " if it.get("clause") else ""
                out.append(f"- **{prefix}{it['name']}:** {it['snippet']} -> {it['suggest']}")
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
    out.append(f"Karar: {decision}") if audience == "Freelancer" else out.append(f"Risk matrisi: yüksek={high}, orta={mid}, düşük={low}. Karar: {decision}")
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
    out.append("### ✅ İmzalamadan Önce 3 Düzeltme" if audience == "Freelancer" else "### ✅ Öncelikli Revizyonlar (3 madde)")
    if top3:
        out.extend([f"- {s}" for s in top3])
    return {
        "markdown": "\n".join(out),
        "score": total_score,
        "high": high,
        "mid": mid,
        "low": low,
        "suggestions": list({i["suggest"] for i in risk_items}),
        "risks": [{"name": r["name"], "snippet": r["snippet"], "suggest": r["suggest"], "weight": r["weight"], "clause": r.get("clause", "")} for r in risk_items],
        "audience": audience
    }