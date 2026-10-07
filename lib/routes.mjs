// Market pages use the path as the authority; shared detail/history pages use the query.
export function marketForPage(path,queryMarket='') {
 if(path.endsWith('/japan.html'))return 'JP';
 if(path.endsWith('/us.html'))return 'US';
 return ['jp','japan'].includes(queryMarket.toLowerCase())?'JP':'US';
}
export const overviewFile=market=>market==='JP'?'japan.html':'us.html';
export function marketPageURL(state,market=state.market) {
 const params=new URLSearchParams({data:state.mode??'live',market:market.toLowerCase(),period:state.period});
 if(state.key)params.set('date',state.key);
 if(market===state.market){params.set('theme',state.researchTheme??'all');params.set('setups',state.setupFilter??'candidate');params.set('lifecycle',state.lifecycleFilter??'all');}
 return `${overviewFile(market)}?${params}`;
}
