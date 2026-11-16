# マイ時刻表 v1.0

公開アプリ: https://smatxsmat-stack.github.io/my-timetable/

専用リポジトリ: https://github.com/smatxsmat-stack/my-timetable

GitHub Actions初回監視・テスト・公開成功（2026-11-17）。毎日09:15 JST。

Galaxy A36向けの静的PWA。出発地をタップし、日本時間の現在時刻以降の登録便を路線横断で発車順に表示します。前回の出発地は端末に保存。行き／帰り、指定日時、手動曜日、端末への追加便も利用できます。

## 使う

公開URLをGalaxyのChromeで開き、メニュー →「ホーム画面に追加」または「アプリをインストール」。初回オンライン表示後にオフライン利用できます。表示対象は登録便であり、運休・遅延・臨時列車をリアルタイム取得するアプリではありません。端末に追加した便は常に未検証表示です。

`dist/index.html` を直接開く方法も残しています（埋め込みデータで動作）。PWAのインストールとService WorkerにはHTTPSまたはlocalhostが必要です。ZIPを端末で開くだけではPWAにはなりません。

## 元の168件の照合

2026-11-16に公式HTML/PDFの発着駅・同一列・運転日注記を確認しました。北しなの線57件、長野電鉄78件、バス33件を維持しています。

- 三才発7件の発時刻を修正。旧値は北長野発でした。
- 運行曜日5件を修正（上の7件と2件重複）。平日限定列車は12/30～1/3も運休。
- 長野電鉄の上りB特急4件の種別表示を補完。
- バス33件の発着時刻・曜日条件は一致。旧 `holiday` は土日祝を指していたため `weekend` に明確化。
- `evidence/original-v03.json` に元データを変更せず保存。`evidence/verification-168.json` に便ごとの新旧値と結果を保存。
- 全便網羅ではありません。北しなの線には元版にない便があり、今回追加していません。

公式改正日：北しなの線2026-03-14、長野電鉄2021-03-13、長電バス2026-03-30。最終照合日と取得確認日は別々に管理します。

## GitHub Actionsを実際に有効にする

1. このZIPのプロジェクト内のファイルをGitHubリポジトリの `main` ブランチ直下に配置。隠しフォルダ `.github` も必要です。
2. Settings → Pages → Build and deployment の Source を **GitHub Actions** に設定。
3. Actionsを有効にし、ワークフローがContentsとIssuesへ書き込めることを確認。保護ブランチで直接pushを禁止している場合は運用に合わせた設定が必要です。
4. Actions → Verify timetables and deploy → Run workflow を実行。
5. 成功したDeployのURLをGalaxyに登録。Issue通知はGitHubリポジトリをWatchし、GitHubの通知設定で受け取ります。

毎日09:15 JSTに監視予定です。GitHub側の遅延やスケジュール停止はあり得るため、最終確認日も確認してください。専用リポジトリは https://github.com/smatxsmat-stack/my-timetable です。CITY PULSEとは独立しています。GitHub Actionsの初回成功とPagesの公開を確認済みです。

参考：[GitHub公式のPagesワークフロー](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)、[PWAのインストール条件](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable)。

## 更新の安全条件

- バス：公式2系統を取得し、4つの曜日／方向表、列数、停留所、全注記、★の定義、改正日、時刻形式、発着順、重複を検証。**既知の表構造と注記が完全一致する時刻変更だけ**自動反映します。
- 便数、停留所、注記、曜日ルールなどの変更は保留。新旧表のdiffと旧／新時刻データをActions artifactへ保存します。
- 将来施行のダイヤは施行日まで保留。新旧併載や系統間で異なる改正日は保留。
- 鉄道：今回の公式PDFと目視確認済みスナップショットを照合。PDF本文または案内ページが変われば自動反映しません。PDFリンクの差し替えも検知し、新PDFとテキストdiffを保存。テキスト抽出が失敗しても時刻を推測しません。
- 取得失敗・検証失敗は対象路線の旧時刻を維持し、画面に再検証が必要と表示。`lastVerified` は更新しません。Issueにログ・比較資料へのリンクを通知します。
- 最後に検証を通過した資料のハッシュを保持。未検証の変更を新しい基準として自動採用しません。
- 内閣府CSVの祝日（振替休日・国民の休日を含む）を利用。2027年末まで収録。範囲外は自動判定せず警告します。過去の祝日改変や不完全なCSVは保留します。

鉄道を手動更新する際は公式PDFの全列と運転日注記を再確認し、`data.json`、`evidence/approved-rail.json`、`evidence/rail-pairs.json`、公式ファイル、`source-state.json` を一緒にレビューして更新してください。ハッシュだけの書き換えは禁止です。既存の照合記録 `verification-168.json` は初期版の監査記録として維持してください。

## 開発とテスト

Python 3.9以上（CIは3.12）、Node.js 22。画面は依存ライブラリなし。

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
node --test tests/*.test.cjs
python build.py
python -m http.server 8765 --directory dist
```

監視を実行する場合：`python tools/check_updates.py`。テスト用には `--fixtures evidence --date 2026-11-16` を指定できます（作業コピーで実行）。pdfplumberは変更PDFの参考diff用であり、鉄道の自動更新を許可するものではありません。

元のbuild.py/upgrade.py/finish.pyは旧データを上書きするため継承せず、新しいbuild.pyへ置き換えました。元ZIPは別途原本として保持してください。

## 公式出典

- [しなの鉄道時刻表](https://www.shinanorailway.co.jp/rail-info/time-table/)
- [長野電鉄時刻表](https://www.nagaden-net.co.jp/info/timetable/)
- [長電バス63](https://www.nagadenbus.co.jp/local/diagram/diagram_p.php?route=NGN02)
- [長電バス64](https://www.nagadenbus.co.jp/local/diagram/diagram_p.php?route=NGN04)
- [内閣府の祝日](https://www8.cao.go.jp/chosei/shukujitsu/gaiyou.html)

`source-state.json` に取得元URLとSHA-256、`evidence/` に照合時の資料を保存しています。

## Issue通知

未検証の変更や取得失敗だけでなく、検証を通過した自動更新もIssueで通知します。同一の未解決状態では再通知せず、資料のハッシュやエラー内容が変わったときだけコメントで通知します。手動実行の notification_test をオンにすると、時刻を変更せず通知の動作確認ができます。
