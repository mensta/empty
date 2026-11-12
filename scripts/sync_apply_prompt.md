あなたは、アップロード済みのデータを物件候補アーティファクトの datasets に反映するだけです。ページは変えません。

対象アーティファクト: __URL__

手順:
1. ArtifactData の get で、datasets の candidates / plans / conditions の現在の version を読みます (url = 対象、collection = datasets、doc_id = 各名前)。
2. ArtifactData の batch で、次の3件を一度に送ります。各 entry の if_version には手順1で読んだ version を入れます。file_path は下の値をそのまま使い、中身は読まないでください。
   - op = update, collection = datasets, doc_id = candidates, file_path = __DOC_CANDIDATES__
   - op = update, collection = datasets, doc_id = plans, file_path = __DOC_PLANS__
   - op = update, collection = datasets, doc_id = conditions, file_path = __DOC_CONDITIONS__
3. 手順2が成功したら、古い blob を Artifact の delete で削除します (url = 対象、path = id)。削除対象: __OLD_BLOBS__ (空なら何もしない)。
4. 手順2が失敗したら、新しい blob を Artifact の delete で削除します (path = id)。削除対象: __NEW_BLOBS__ 。古い blob は削除しないでください。

最後に、指定された JSON 形式だけで結果を返してください。
- ok: 手順2が成功したら true
- versions: 手順2の結果の candidates / plans / conditions の version
- deleted: 削除できた id
- errors: 失敗や確かめられなかった点 (なければ空)

値は推測で埋めないでください。確かめられないものは errors に書きます。
ページ (files/index.html)、data/*.json、サイトへの取得処理には触れないでください。
