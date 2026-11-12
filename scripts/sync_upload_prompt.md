あなたは次の3ファイルを、物件候補アーティファクトにアップロードするだけです。

対象アーティファクト: __URL__

1. 3ファイルを、それぞれ別の Artifact 呼び出しでアップロードしてください (url = 対象、asset = true、file_path = 下のパス)。1回の呼び出しに1ファイルだけ。
   - candidates: __CANDIDATES__
   - plans: __PLANS__
   - conditions: __CONDITIONS__
2. 結果の `/_blob/<id>` から 32 桁の id を控えます。id を推測で作らないでください。

最後に、指定された JSON 形式だけで結果を返してください。
- ok: 3件とも成功したら true
- blobs: candidates / plans / conditions の id
- errors: 失敗した内容 (なければ空)

ページ・データファイル・ほかのアーティファクトには触れないでください。
