const fs=require('node:fs'),crypto=require('node:crypto');
module.exports=async function notify({github,context,state,comparison={},outcome='success',test=false}){
 const failed=outcome!=='success',review=failed||state.alerts.length>0;
 if(!test&&!review&&!state.changedSources?.length)return {sent:false};
 const title=test?'[動作確認] 時刻表のIssue通知':review?'時刻表の変更確認が必要です':'時刻表の自動更新を確認しました';
 const signature=crypto.createHash('sha256').update(JSON.stringify({test,failed,alerts:state.alerts,changes:(state.changedSources||[]).map(k=>[k,comparison.observed?.[k]?.sha256]),updated:state.updatedRoutes})).digest('hex');
 const marker=`<!-- timetable-notification:${signature} -->`;
 const run=`${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
 const body=[test?'Issue通知の動作確認です。実際の時刻変更ではありません。':review?'公式資料の変更または取得・検証エラーがあります。検証できない路線の既存時刻は維持しています。':'公式変更を検証し、自動更新しました。',`監視処理: ${failed?'異常終了':'完了'}`,`変更元: ${(state.changedSources||[]).join(', ')||'なし'}`,`更新路線: ${(state.updatedRoutes||[]).join(', ')||'なし'}`,...state.alerts.map(x=>`- ${x.source}: ${x.reason}`),`[比較資料・実行ログ](${run})`,test?'テスト完了後、このIssueは閉じて構いません。':'鉄道PDFや未知の表構造は手動再検証が必要です。',marker].join('\n\n');
 const issues=await github.paginate(github.rest.issues.listForRepo,{...context.repo,state:'open',creator:'github-actions[bot]',per_page:100});
 const existing=issues.find(x=>!x.pull_request&&x.title===title);
 if(existing){
  if(existing.body?.includes(marker))return {sent:false,deduplicated:true};
  await github.rest.issues.createComment({...context.repo,issue_number:existing.number,body});
  await github.rest.issues.update({...context.repo,issue_number:existing.number,body});
 }else await github.rest.issues.create({...context.repo,title,body});
 return {sent:true};
};
