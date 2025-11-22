import json
from app import advanced_analyze

def main():
    text = "Taraflar arasında hizmet sağlanacaktır. Gizlilik 6 ay ile sınırlıdır. Ödeme vadesi 30 gündür."
    res = advanced_analyze(text, audience="Freelancer")
    assert isinstance(res, dict) and "markdown" in res and res["score"] >= 1
    print(json.dumps({"score": res["score"], "len": len(res["markdown"]) }))

if __name__ == "__main__":
    main()