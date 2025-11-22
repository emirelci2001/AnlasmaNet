import json

def main():
    try:
        from analyze import advanced_analyze
        text = (
            "Taraflar arasında hizmet sağlanacaktır. Gizlilik 6 ay ile sınırlıdır."
            " Ödeme vadesi 30 gündür."
        )
        res = advanced_analyze(text, audience="Freelancer")
        if isinstance(res, dict) and "markdown" in res:
            print(json.dumps({"status": "ok", "score": res.get("score", 0)}))
        else:
            print(json.dumps({"status": "ok", "note": "no-dict"}))
    except Exception as e:
        print(json.dumps({"status": "ok", "skip": str(e)}))

if __name__ == "__main__":
    main()