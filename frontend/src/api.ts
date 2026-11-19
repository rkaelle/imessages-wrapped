import { useEffect, useState } from 'react';
import type { Detail, Summary } from './types';
export async function request<T>(path:string,signal?:AbortSignal,post=false):Promise<T> {
 const response=await fetch(`/api${path}`,{signal,method:post?'POST':'GET',headers:post?{'X-Wrapped-Client':'local'}:{}});
 const body=await response.json();
 if(!response.ok) throw new Error(body.error||'The local server could not be reached.');
 return body;
}
export function useResource<T>(path:string|null,revision=0) {
 const [state,setState]=useState<{data:T|null;error:string|null;loading:boolean}>({data:null,error:null,loading:true});
 useEffect(()=>{
  if(!path){setState({data:null,error:null,loading:false});return;}
  const controller=new AbortController();
  setState({data:null,error:null,loading:true});
  request<T>(path,controller.signal).then(data=>setState({data,error:null,loading:false})).catch(e=>{if(e.name!=='AbortError')setState({data:null,error:e.message,loading:false});});
  return ()=>controller.abort();
 },[path,revision]);
 return state;
}

const emptyRhythm=()=>Array.from({length:7},()=>Array(24).fill(0));
/** Fills fields a server running older analytics code would omit, so the UI degrades instead of crashing. */
export function withSummaryDefaults(s:Summary):Summary {
 return {...s,stale:!s.rhythm||!s.habits,rhythm:s.rhythm??emptyRhythm(),streak:s.streak??null,late_night:s.late_night??null,calendar:s.calendar??null,top_groups:s.top_groups??[],
  top_people:s.top_people.map(p=>({...p,sparkline:p.sparkline??[]})),
  streaks:s.streaks??{longest:[],current:[]},habits:s.habits??null,laughs:s.laughs??{years:[],series:[]}};
}
export function withDetailDefaults(d:Detail):Detail {
 return {...d,rhythm:d.rhythm??emptyRhythm(),streak:d.streak??null,late_night:d.late_night??null,initiations:d.initiations??{you:0,them:0,gap_hours:6},
  reply_histogram:d.reply_histogram??{bins:[],you:[],them:[]},words:d.words??[],media:d.media??null};
}
