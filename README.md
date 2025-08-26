# mytool

PC操作を記録・再生するためのツールです。  
記録した操作はJSONファイルとして保存され、後で再生できます。

---

## フォルダ構成
```
mytool/
├── core/ # 記録・再生のメインコード
│ ├── record_core.py
│ └── replay_core.py
├── cli.py
├── records/ # 記録されたJSONファイルが保存されるフォルダ
├── requirements.txt
└── README.md
```

---

## 必要環境

- Python 3.10.4
- ライブラリは `requirements.txt` からインストール可能

```
pip install -r requirements.txt
```
---

## 使い方

### 記録
操作を記録するには以下を実行します：

```
python cli.py record
```

制御キーは(s,w,q,h)です：
  * sは記録開始のコマンド
  * wは記録保存のコマンド
  * qは停止のコマンド
  * hはヘルプのコマンド
