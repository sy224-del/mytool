# mytool

PC操作を記録・再生するためのツールです。  
記録した操作はJSONファイルとして保存され、後で再生できます。

---

## フォルダ構成
```
mytool/
├── core/ # 記録・再生のメインコード
│ ├── record_core.py
│ ├── replay_core.py
│ └── cli.py
├── records/ # 記録されたJSONファイルが保存されるフォルダ
├── requirements.txt
└── README.md
```

---

## 必要環境

- Python 3.10.4
- ライブラリは `requirements.txt` からインストール可能

```bash
pip install -r requirements.txt
